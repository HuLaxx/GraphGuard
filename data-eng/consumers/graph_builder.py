"""
GraphGuard - Graph Builder Consumer
====================================
File: data-eng/consumers/graph_builder.py
Reference: Specification.md Lines 842-907

Goal: Build real-time transaction graph in Neo4j from Kafka events.

Gotchas (from spec):
- Neo4j writes are slow (50-100ms) - batch 10-20 transactions per write
- Use MERGE instead of CREATE to avoid duplicate nodes
"""

import os
import json
from math import isfinite
from typing import Optional, List
from datetime import datetime

from confluent_kafka import Consumer, Producer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField
from neo4j import GraphDatabase
import structlog

from transaction_ledger import TransactionLedger

# Configure structured logging
logger = structlog.get_logger(__name__)


# ============================================
# Configuration (Spec Lines 851-856)
# ============================================

def get_consumer_config() -> dict:
    """
    Kafka consumer configuration for graph builder.
    Reference: Specification.md Lines 851-856
    """
    return {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'group.id': os.getenv('KAFKA_GROUP_ID', 'graph-builder'),
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,  # Commit only after durable graph write; at-least-once
        'session.timeout.ms': 60000,  # Gotcha: Prevent rebalancing during slow processing
        'heartbeat.interval.ms': 3000,
        'max.poll.interval.ms': 300000,  # 5 minutes
        'client.id': 'graphguard-graph-builder'
    }


def get_neo4j_config() -> dict:
    """Neo4j connection configuration."""
    return {
        'uri': os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        'user': os.getenv('NEO4J_USER', 'neo4j'),
        'password': os.getenv('NEO4J_PASSWORD', 'graphguard_dev')
    }


def get_schema_registry_config() -> dict:
    """Schema Registry configuration."""
    return {
        'url': os.getenv('SCHEMA_REGISTRY_URL', 'http://localhost:8081')
    }


# ============================================
# Cypher Queries (Spec Lines 865-888)
# ============================================

CREATE_TRANSACTION_EDGE_BATCH = """
// Only the original canonical content is allowed to create graph relationships.
// Existing nodes from older, unverified pipelines must be reconciled first.
UNWIND $transactions AS txn
MERGE (t:Transaction {id: txn.transaction_id})
ON CREATE SET t.payload_sha256 = txn.payload_sha256,
              t.amount = txn.amount,
              t.timestamp = txn.timestamp,
              t.currency = txn.currency,
              t.fraud_score = 0.0,
              t.status = 'PENDING'
WITH txn, t
WHERE t.payload_sha256 = txn.payload_sha256
MERGE (u:User {id: txn.user_id})
ON CREATE SET u.created_at = timestamp()
MERGE (m:Merchant {id: txn.merchant_id})
ON CREATE SET m.created_at = timestamp()
MERGE (d:Device {id: txn.device_id})
ON CREATE SET d.first_seen = txn.timestamp
SET d.last_seen = CASE WHEN d.last_seen IS NULL OR d.last_seen < txn.timestamp
                       THEN txn.timestamp ELSE d.last_seen END
MERGE (u)-[:PERFORMED]->(t)
MERGE (t)-[:PAID_TO]->(m)
MERGE (t)-[:USED_DEVICE]->(d)
RETURN count(t) AS applied
"""


# ============================================
# Graph Builder Consumer Class
# ============================================

class GraphBuilder:
    """
    Kafka consumer that builds transaction graph in Neo4j.
    Implements batching for performance (Gotcha: 10-20 txns per batch).
    """
    
    TOPIC = 'transactions.raw'
    DLQ_TOPIC = 'transactions.dlq'
    BATCH_SIZE = 15  # Gotcha: Batch 10-20 for performance
    
    def __init__(
        self,
        consumer_config: Optional[dict] = None,
        neo4j_config: Optional[dict] = None
    ):
        self.consumer_config = consumer_config or get_consumer_config()
        self.neo4j_config = neo4j_config or get_neo4j_config()
        
        # Initialize Kafka consumer
        self.consumer = Consumer(self.consumer_config)
        self.consumer.subscribe([self.TOPIC])
        
        # Initialize DLQ producer
        self.dlq_producer = Producer({
            'bootstrap.servers': self.consumer_config['bootstrap.servers']
        })

        # Initialize Schema Registry client + Avro deserializer
        self.schema_registry = SchemaRegistryClient(get_schema_registry_config())
        self.avro_deserializer = None
        # JSON payloads are reserved for explicitly opted-in synthetic fixtures.
        # Silently treating a registry outage as bad JSON can lose valid Avro events.
        self.allow_json_fallback = (
            os.getenv("GRAPHGUARD_JSON_FIXTURE_MODE", "false").lower() == "true"
        )
        schema_path = os.path.join(
            os.path.dirname(__file__),
            '..', 'schemas', 'transaction_event.avsc'
        )
        try:
            with open(schema_path, 'r') as f:
                schema_str = f.read()
            self.avro_deserializer = AvroDeserializer(
                self.schema_registry,
                schema_str
            )
        except Exception as e:
            logger.warning("Failed to load Avro schema", error=str(e), path=schema_path)
        
        # Initialize Neo4j driver
        self.neo4j_driver = GraphDatabase.driver(
            self.neo4j_config['uri'],
            auth=(self.neo4j_config['user'], self.neo4j_config['password'])
        )
        
        # Verify Neo4j connection
        self.neo4j_driver.verify_connectivity()
        
        # A durable, local source ledger is written before any derived graph write.
        # This development implementation is NOT distributed exactly-once.
        ledger_path = os.getenv(
            "GRAPHGUARD_LEDGER_PATH",
            os.path.join(os.path.dirname(__file__), "..", "..", ".local", "transaction-ledger.sqlite3"),
        )
        self.ledger = TransactionLedger(ledger_path)

        # Transaction buffer for batching
        self.buffer: List[dict] = []
        self.pending_messages = []
        
        logger.info(
            "GraphBuilder initialized",
            bootstrap_servers=self.consumer_config['bootstrap.servers'],
            topic=self.TOPIC,
            neo4j_uri=self.neo4j_config['uri']
        )
    
    def _create_indexes(self) -> None:
        """Enforce graph identity before accepting source events."""
        with self.neo4j_driver.session() as session:
            for label, name in (
                ("User", "graphguard_user_id_unique"),
                ("Merchant", "graphguard_merchant_id_unique"),
                ("Device", "graphguard_device_id_unique"),
                ("Transaction", "graphguard_transaction_id_unique"),
            ):
                session.run(
                    f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.id IS UNIQUE"
                ).consume()
            session.run(
                "CREATE INDEX txn_timestamp_index IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp)"
            ).consume()

        logger.info("Neo4j identity constraints created/verified")

    def _create_transaction_edge(self, txn: dict) -> None:
        """Single-event projection follows the same identity safety as a batch."""
        self._create_transaction_edges_batch([txn])

    @staticmethod
    def _write_batch(tx, transactions: List[dict]) -> None:
        result = tx.run(CREATE_TRANSACTION_EDGE_BATCH, transactions=transactions)
        record = result.single()
        if record is None or record["applied"] != len(transactions):
            # Raising within execute_write rolls back the entire graph transaction.
            # An existing graph without payload_sha256 requires migration, not overwrite.
            raise RuntimeError("Neo4j transaction identity mismatch; refusing graph projection")

    def _create_transaction_edges_batch(self, transactions: List[dict]) -> None:
        """Atomic graph projection; count and identity checked before commit."""
        with self.neo4j_driver.session() as session:
            session.execute_write(self._write_batch, transactions)

        logger.info("Batch written to Neo4j", batch_size=len(transactions))

    def _send_to_dlq(self, message_value: bytes, error: str) -> None:
        """Publish a permanently invalid message to DLQ and require an ACK.

        On a failed DLQ delivery, callers must retain the original Kafka offset
        for replay. Infrastructure/Neo4j outages are *not* poison messages.
        """
        delivery_errors = []
        acknowledged = []

        def on_delivery(delivery_error, _message):
            if delivery_error is not None:
                delivery_errors.append(str(delivery_error))
            else:
                acknowledged.append(True)

        self.dlq_producer.produce(
            topic=self.DLQ_TOPIC,
            value=message_value,
            headers={'error': error[:200].encode('utf-8')},
            on_delivery=on_delivery,
        )
        remaining = self.dlq_producer.flush(timeout=10)
        if remaining or delivery_errors or not acknowledged:
            raise RuntimeError("DLQ delivery not acknowledged; Kafka offset was not committed")

        logger.warning("Permanently invalid event routed to DLQ", error=error[:200])

    def _flush_buffer(self) -> None:
        """Graph write before synchronous offset commit: replay on transient failures.

        Graph upserts must remain idempotent: a crash after graph commit but
        before Kafka offset commit will legitimately replay some messages.
        """
        if not self.buffer:
            return

        try:
            self._create_transaction_edges_batch(self.buffer)
            for msg in self.pending_messages:
                committed = self.consumer.commit(message=msg, asynchronous=False)
                if committed and any(getattr(part, "error", None) for part in committed):
                    raise RuntimeError("Kafka returned an offset-commit error")
        except Exception as exc:
            logger.error(
                "Graph write or offset commit failed; retaining uncommitted batch",
                error=str(exc),
                transactions=len(self.buffer),
            )
            # Do not classify a Neo4j outage as bad input, DLQ valid records, or
            # discard the buffer. The caller may retry or restart from Kafka.
            raise

        logger.info("Graph batch persisted and offsets committed", transactions=len(self.buffer))
        self.buffer = []
        self.pending_messages = []

    def process_message(self, msg) -> None:
        """Decode/validate events; route only malformed input to DLQ.

        Database failures happen outside the validation handler so they
        propagate without advancing Kafka offsets.
        """
        value = msg.value()
        try:
            # Confluent wire framing: 0x00 + schema ID + Avro payload.
            # A registry outage or undecodable Avro is an infrastructure/contract
            # fault, not permission to parse bytes as JSON and advance offsets.
            if isinstance(value, bytes) and value.startswith(b"\x00"):
                if self.avro_deserializer is None:
                    raise RuntimeError(
                        "Avro decoder unavailable; retain offset for replay"
                    )
                try:
                    txn = self.avro_deserializer(
                        value, SerializationContext(self.TOPIC, MessageField.VALUE)
                    )
                except Exception as exc:
                    raise RuntimeError(
                        "Avro/Schema Registry decode failed; retain offset for replay"
                    ) from exc
            elif self.allow_json_fallback:
                # Only explicitly opted-in synthetic test fixtures accept JSON.
                txn = json.loads(value.decode("utf-8")) if isinstance(value, bytes) else value
            else:
                raise RuntimeError(
                    "Unexpected non-Avro transaction; retain offset for investigation"
                )

            if not isinstance(txn, dict):
                raise ValueError("Transaction must be a JSON object")
            required_ids = ("transaction_id", "user_id", "merchant_id", "device_id")
            if any(not isinstance(txn.get(k), str) or not txn[k].strip() for k in required_ids):
                raise ValueError("Transaction contains missing or invalid entity identifiers")
            amount = txn.get("amount")
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not isfinite(amount) or amount <= 0:
                raise ValueError("Transaction amount must be positive and finite")
            currency = txn.get("currency")
            if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha() or currency.upper() != currency:
                raise ValueError("Transaction currency must be a three-letter uppercase code")
            event_time = txn.get("timestamp")
            if isinstance(event_time, datetime):
                if event_time.tzinfo is None or event_time.utcoffset() is None:
                    raise ValueError("Transaction timestamps must include timezone")
                txn["timestamp"] = int(event_time.timestamp() * 1000)
            elif isinstance(event_time, bool) or not isinstance(event_time, int) or event_time <= 0:
                raise ValueError("Transaction timestamp must be a positive epoch-millis integer")
            version = txn.get("schema_version", 1)
            if type(version) is not int or version != 1:
                raise ValueError("Unsupported transaction schema_version")
            event_key = txn.get("idempotency_key")
            if not isinstance(event_key, str) or len(event_key) != 64 or any(c not in "0123456789abcdef" for c in event_key):
                raise ValueError("Transaction idempotency key must be a SHA-256 hex digest")
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError) as exc:
            logger.warning("Invalid transaction input", error=str(exc))
            # Commit the earlier valid events before any later poison offset.
            if self.buffer:
                self._flush_buffer()
            self._send_to_dlq(value, f"InvalidTransaction: {type(exc).__name__}")
            self.consumer.commit(message=msg, asynchronous=False)
            return

        # Durable source write is deliberately outside the validation handler.
        # Storage failures retain Kafka offsets and are never classified as poison.
        receipt = self.ledger.record(
            txn, topic=msg.topic(), partition=msg.partition(), offset=msg.offset()
        )
        if receipt.status == "conflict":
            if self.buffer:
                self._flush_buffer()
            # Keep the original immutable source and graph untouched.
            self._send_to_dlq(value, "TransactionIdConflict")
            self.consumer.commit(message=msg, asynchronous=False)
            logger.warning("Transaction identity conflict quarantined", transaction_id=txn["transaction_id"])
            return
        txn["payload_sha256"] = receipt.payload_hash
        self.buffer.append(txn)
        self.pending_messages.append(msg)
        logger.debug("Transaction buffered", transaction_id=txn["transaction_id"], buffer_size=len(self.buffer))
        if len(self.buffer) >= self.BATCH_SIZE:
            # This is deliberately outside the validation try/except. Neo4j
            # outage must not turn legitimate transactions into a DLQ loss.
            self._flush_buffer()

    def run(self, max_messages: Optional[int] = None) -> None:
        """
        Main consumer loop.
        Reference: Specification.md Lines 890-903
        
        Args:
            max_messages: Stop after processing this many messages (for testing)
        """
        self._create_indexes()
        
        messages_processed = 0
        
        logger.info("Starting graph builder consumer loop")
        
        try:
            while True:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    # No message, check if we should flush partial buffer
                    if self.buffer and len(self.buffer) > 0:
                        self._flush_buffer()
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug("Reached end of partition")
                    else:
                        logger.error("Consumer error", error=str(msg.error()))
                    continue
                
                self.process_message(msg)
                messages_processed += 1
                
                # Check if we should stop (for testing)
                if max_messages and messages_processed >= max_messages:
                    logger.info("Reached max messages", count=max_messages)
                    break
                    
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            # Always close connections, even if flushing raises due to a DB outage.
            try:
                self._flush_buffer()
            finally:
                self.close()
    
    def close(self) -> None:
        """Clean up resources."""
        self.consumer.close()
        self.neo4j_driver.close()
        self.ledger.close()
        self.dlq_producer.flush()
        
        logger.info("GraphBuilder closed")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Graph Builder - Kafka to Neo4j consumer")
    parser.add_argument("--kafka", default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--neo4j", default="bolt://localhost:7687", help="Neo4j URI")
    parser.add_argument("--max-messages", type=int, help="Max messages to process (for testing)")
    args = parser.parse_args()
    
    # Set environment
    os.environ['KAFKA_BOOTSTRAP_SERVERS'] = args.kafka
    os.environ['NEO4J_URI'] = args.neo4j
    
    builder = GraphBuilder()
    builder.run(max_messages=args.max_messages)
