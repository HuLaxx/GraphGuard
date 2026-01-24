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
from typing import Optional, List
from datetime import datetime

from confluent_kafka import Consumer, Producer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer
from confluent_kafka.serialization import SerializationContext, MessageField
from neo4j import GraphDatabase
import structlog

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
        'enable.auto.commit': False,  # Manual commit for exactly-once
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

CREATE_TRANSACTION_EDGE = """
MERGE (u:User {id: $user_id})
ON CREATE SET u.created_at = timestamp()

MERGE (m:Merchant {id: $merchant_id})
ON CREATE SET m.created_at = timestamp()

MERGE (d:Device {id: $device_id})
ON CREATE SET d.first_seen = $timestamp
SET d.last_seen = $timestamp

MERGE (t:Transaction {id: $transaction_id})
ON CREATE SET t.amount = $amount,
              t.timestamp = $timestamp,
              t.currency = $currency,
              t.fraud_score = 0.0,
              t.status = 'PENDING'
ON MATCH SET t.amount = $amount,
             t.timestamp = $timestamp,
             t.currency = $currency

MERGE (u)-[:PERFORMED]->(t)
MERGE (t)-[:PAID_TO]->(m)
MERGE (t)-[:USED_DEVICE]->(d)
"""

# Batch version for performance
CREATE_TRANSACTION_EDGE_BATCH = """
UNWIND $transactions AS txn
MERGE (u:User {id: txn.user_id})
ON CREATE SET u.created_at = timestamp()

MERGE (m:Merchant {id: txn.merchant_id})
ON CREATE SET m.created_at = timestamp()

MERGE (d:Device {id: txn.device_id})
ON CREATE SET d.first_seen = txn.timestamp
SET d.last_seen = txn.timestamp

MERGE (t:Transaction {id: txn.transaction_id})
ON CREATE SET t.amount = txn.amount,
              t.timestamp = txn.timestamp,
              t.currency = txn.currency,
              t.fraud_score = 0.0,
              t.status = 'PENDING'
ON MATCH SET t.amount = txn.amount,
             t.timestamp = txn.timestamp,
             t.currency = txn.currency

MERGE (u)-[:PERFORMED]->(t)
MERGE (t)-[:PAID_TO]->(m)
MERGE (t)-[:USED_DEVICE]->(d)
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
        """Create Neo4j indexes for performance."""
        with self.neo4j_driver.session() as session:
            # User index
            session.run("CREATE INDEX user_id_index IF NOT EXISTS FOR (u:User) ON (u.id)")
            # Merchant index
            session.run("CREATE INDEX merchant_id_index IF NOT EXISTS FOR (m:Merchant) ON (m.id)")
            # Device index
            session.run("CREATE INDEX device_id_index IF NOT EXISTS FOR (d:Device) ON (d.id)")
            # Transaction index
            session.run("CREATE INDEX txn_id_index IF NOT EXISTS FOR (t:Transaction) ON (t.id)")
            session.run("CREATE INDEX txn_timestamp_index IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp)")
        
        logger.info("Neo4j indexes created/verified")
    
    def _create_transaction_edge(self, txn: dict) -> None:
        """
        Create a single transaction edge in Neo4j.
        Reference: Specification.md Lines 863-888
        """
        with self.neo4j_driver.session() as session:
            session.run(
                CREATE_TRANSACTION_EDGE,
                user_id=txn['user_id'],
                merchant_id=txn['merchant_id'],
                device_id=txn['device_id'],
                amount=txn['amount'],
                timestamp=txn['timestamp'],
                transaction_id=txn['transaction_id'],
                currency=txn.get('currency', 'USD')
            )
    
    def _create_transaction_edges_batch(self, transactions: List[dict]) -> None:
        """
        Create multiple transaction edges in one query (batched).
        Gotcha: Batch 10-20 transactions for performance.
        """
        with self.neo4j_driver.session() as session:
            session.run(CREATE_TRANSACTION_EDGE_BATCH, transactions=transactions)
        
        logger.info(
            "Batch written to Neo4j",
            batch_size=len(transactions)
        )
    
    def _send_to_dlq(self, message_value: bytes, error: str) -> None:
        """Send failed message to Dead Letter Queue."""
        self.dlq_producer.produce(
            topic=self.DLQ_TOPIC,
            value=message_value,
            headers={'error': error.encode('utf-8')}
        )
        self.dlq_producer.flush()
        
        logger.warning(
            "Message sent to DLQ",
            error=error
        )
    
    def _flush_buffer(self) -> None:
        """Flush the transaction buffer to Neo4j."""
        if not self.buffer:
            return
        
        try:
            self._create_transaction_edges_batch(self.buffer)
            
            # Commit offsets for processed messages
            for msg in self.pending_messages:
                self.consumer.commit(message=msg)
            
            logger.info(
                "Buffer flushed and offsets committed",
                transactions=len(self.buffer)
            )
            
        except Exception as e:
            logger.error(
                "Failed to flush buffer",
                error=str(e),
                transactions=len(self.buffer)
            )
            # Send all to DLQ
            for msg in self.pending_messages:
                self._send_to_dlq(msg.value(), str(e))
                self.consumer.commit(message=msg)
        
        # Clear buffer
        self.buffer = []
        self.pending_messages = []
    
    def process_message(self, msg) -> None:
        """Process a single Kafka message."""
        try:
            # Deserialize message
            value = msg.value()
            txn = None
            if isinstance(value, bytes) and self.avro_deserializer is not None:
                try:
                    txn = self.avro_deserializer(
                        value,
                        SerializationContext(self.TOPIC, MessageField.VALUE)
                    )
                except Exception as e:
                    logger.warning("Avro deserialization failed", error=str(e))
                    txn = None

            if txn is None:
                if isinstance(value, bytes):
                    txn = json.loads(value.decode('utf-8'))
                else:
                    txn = value

            if not isinstance(txn, dict):
                raise ValueError("Invalid transaction payload")
            
            if isinstance(txn.get('timestamp'), datetime):
                txn['timestamp'] = int(txn['timestamp'].timestamp() * 1000)
            
            # Add to buffer
            self.buffer.append(txn)
            self.pending_messages.append(msg)
            
            logger.debug(
                "Message buffered",
                transaction_id=txn.get('transaction_id'),
                buffer_size=len(self.buffer)
            )
            
            # Flush if buffer is full
            if len(self.buffer) >= self.BATCH_SIZE:
                self._flush_buffer()
                
        except Exception as e:
            logger.error(
                "Failed to process message",
                error=str(e)
            )
            self._send_to_dlq(msg.value(), f"ProcessingError: {e}")
            self.consumer.commit(message=msg)
    
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
            # Flush any remaining messages
            self._flush_buffer()
            self.close()
    
    def close(self) -> None:
        """Clean up resources."""
        self.consumer.close()
        self.neo4j_driver.close()
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
