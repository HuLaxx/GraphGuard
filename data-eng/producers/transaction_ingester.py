"""
GraphGuard - Kafka Transaction Producer
========================================
File: data-eng/producers/transaction_ingester.py
Reference: Specification.md Lines 720-775

Goal: Ingest transactions from payment webhooks (Stripe, Plaid) and publish to Kafka.

Gotchas (from spec):
- Stripe webhooks can duplicate - use idempotency_key
- Set compression='snappy' for 60% size reduction
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Optional, Callable

from confluent_kafka import Producer, KafkaError
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import SerializationContext, MessageField
from pydantic import BaseModel, Field
import structlog

# Configure structured logging
logger = structlog.get_logger(__name__)


# ============================================
# Transaction Event Model (Spec Lines 732-748)
# ============================================

class TransactionEvent(BaseModel):
    """
    Transaction event model for Kafka ingestion.
    Matches Avro schema in schemas/transaction_event.avsc
    """
    transaction_id: str = Field(..., description="Unique transaction ID from payment gateway")
    user_id: str = Field(..., description="User initiating the transaction")
    merchant_id: str = Field(..., description="Merchant receiving the payment")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(..., pattern="^[A-Z]{3}$", description="ISO 4217 currency code")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    device_id: str = Field(..., description="Device fingerprint")
    ip_address: str = Field(..., description="Client IP address")
    card_last4: str = Field(..., pattern="^[0-9]{4}$", description="Last 4 digits of card")
    
    @property
    def idempotency_key(self) -> str:
        """
        Deterministic key to prevent duplicate processing.
        SHA256 hash of transaction_id:timestamp
        """
        return hashlib.sha256(
            f"{self.transaction_id}:{self.timestamp.isoformat()}".encode()
        ).hexdigest()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for Avro serialization."""
        return {
            "transaction_id": self.transaction_id,
            "user_id": self.user_id,
            "merchant_id": self.merchant_id,
            "amount": self.amount,
            "currency": self.currency,
            "timestamp": int(self.timestamp.timestamp() * 1000),  # Avro timestamp-millis
            "device_id": self.device_id,
            "ip_address": self.ip_address,
            "card_last4": self.card_last4,
            "idempotency_key": self.idempotency_key,
            "schema_version": 1
        }


# ============================================
# Kafka Producer Configuration (Spec Lines 750-757)
# ============================================

def get_producer_config() -> dict:
    """
    Kafka producer configuration with idempotent writes (NOT end-to-end exactly-once).
    Reference: Specification.md Lines 750-757
    """
    return {
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
        'acks': 'all',  # Wait for all replicas
        'enable.idempotence': True,  # Producer retry deduplication only
        'max.in.flight.requests.per.connection': 5,
        'retries': 10,
        'compression.type': 'snappy',  # Gotcha: 60% size reduction
        'linger.ms': 5,  # Small batching for throughput
        'batch.size': 16384,
        'client.id': 'graphguard-transaction-producer'
    }


def get_schema_registry_config() -> dict:
    """Schema Registry configuration."""
    return {
        'url': os.getenv('SCHEMA_REGISTRY_URL', 'http://localhost:8081')
    }


# ============================================
# Transaction Producer Class
# ============================================

class TransactionProducer:
    """
    Kafka producer for transaction events with Avro serialization.
    """
    
    TOPIC = 'transactions.raw'
    
    def __init__(
        self,
        producer_config: Optional[dict] = None,
        schema_registry_config: Optional[dict] = None
    ):
        self.producer_config = producer_config or get_producer_config()
        self.schema_registry_config = schema_registry_config or get_schema_registry_config()
        
        # Initialize Schema Registry client
        self.schema_registry = SchemaRegistryClient(self.schema_registry_config)
        
        # Load Avro schema
        schema_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'schemas', 'transaction_event.avsc'
        )
        with open(schema_path, 'r') as f:
            schema_str = f.read()
        
        # Initialize Avro serializer
        self.avro_serializer = AvroSerializer(
            self.schema_registry,
            schema_str,
            to_dict=lambda obj, ctx: obj  # Already a dict
        )
        
        # Initialize Kafka producer
        self.producer = Producer(self.producer_config)
        
        logger.info(
            "TransactionProducer initialized",
            bootstrap_servers=self.producer_config['bootstrap.servers'],
            topic=self.TOPIC
        )
    
    def _delivery_callback(self, err: Optional[KafkaError], msg) -> None:
        """Callback for message delivery confirmation."""
        if err is not None:
            logger.error(
                "Message delivery failed",
                error=str(err),
                topic=msg.topic(),
                partition=msg.partition()
            )
        else:
            logger.debug(
                "Message delivered",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset()
            )
    
    def publish(
        self, 
        transaction: TransactionEvent,
        on_delivery: Optional[Callable] = None
    ) -> None:
        """
        Publish a transaction event to Kafka.
        
        Args:
            transaction: TransactionEvent to publish
            on_delivery: Optional callback for delivery confirmation
        
        Reference: Specification.md Lines 764-771
        """
        callback = on_delivery or self._delivery_callback
        
        try:
            self.producer.produce(
                topic=self.TOPIC,
                key=transaction.idempotency_key.encode('utf-8'),
                value=self.avro_serializer(
                    transaction.to_dict(),
                    SerializationContext(self.TOPIC, MessageField.VALUE)
                ),
                on_delivery=callback
            )
            
            logger.info(
                "Transaction published",
                transaction_id=transaction.transaction_id,
                user_id=transaction.user_id,
                amount=transaction.amount,
                idempotency_key=transaction.idempotency_key[:16] + "..."
            )
            
        except Exception as e:
            logger.error(
                "Failed to publish transaction",
                transaction_id=transaction.transaction_id,
                error=str(e)
            )
            raise
    
    def publish_batch(self, transactions: list[TransactionEvent]) -> None:
        """
        Publish multiple transactions efficiently.
        Batches messages and flushes at the end.
        """
        for txn in transactions:
            self.publish(txn)
        
        # Flush to ensure all messages are sent
        remaining = self.producer.flush(timeout=10)
        
        if remaining > 0:
            logger.warning(
                "Not all messages were delivered",
                remaining=remaining
            )
    
    def flush(self, timeout: float = 10) -> int:
        """
        Wait for all messages to be delivered.
        
        Returns:
            Number of messages still in queue after timeout
        """
        return self.producer.flush(timeout=timeout)
    
    def close(self) -> None:
        """Flush and close the producer."""
        self.flush()
        logger.info("TransactionProducer closed")


# ============================================
# Stripe Webhook Handler
# ============================================

def parse_stripe_webhook(payload: dict) -> TransactionEvent:
    """
    Parse Stripe webhook payload into TransactionEvent.
    
    Gotcha: Stripe webhooks can send duplicates - handled by idempotency_key
    """
    charge = payload.get('data', {}).get('object', {})
    
    return TransactionEvent(
        transaction_id=charge.get('id', ''),
        user_id=charge.get('customer', ''),
        merchant_id=charge.get('destination', 'default_merchant'),
        amount=charge.get('amount', 0) / 100,  # Stripe uses cents
        currency=charge.get('currency', 'USD').upper(),
        timestamp=datetime.fromtimestamp(charge.get('created', datetime.now(timezone.utc).timestamp()), tz=timezone.utc),
        device_id=charge.get('metadata', {}).get('device_id', 'unknown'),
        ip_address=charge.get('metadata', {}).get('ip_address', '0.0.0.0'),
        card_last4=charge.get('payment_method_details', {}).get('card', {}).get('last4', '0000')
    )


# ============================================
# CLI for Testing
# ============================================

if __name__ == "__main__":
    import argparse
    from faker import Faker
    import random
    
    fake = Faker()
    
    parser = argparse.ArgumentParser(description="Generate and publish test transactions")
    parser.add_argument("--count", type=int, default=10, help="Number of transactions to generate")
    parser.add_argument("--kafka", default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--registry", default="http://localhost:8081", help="Schema Registry URL")
    args = parser.parse_args()
    
    # Override config for CLI
    os.environ['KAFKA_BOOTSTRAP_SERVERS'] = args.kafka
    os.environ['SCHEMA_REGISTRY_URL'] = args.registry
    
    producer = TransactionProducer()
    
    print(f"Generating {args.count} test transactions...")
    
    for i in range(args.count):
        txn = TransactionEvent(
            transaction_id=f"txn_{fake.uuid4()[:8]}",
            user_id=f"user_{random.randint(1000, 9999)}",
            merchant_id=f"merchant_{random.randint(100, 500)}",
            amount=round(random.uniform(10, 5000), 2),
            currency=random.choice(["USD", "EUR", "GBP"]),
            device_id=fake.uuid4()[:16],
            ip_address=fake.ipv4(),
            card_last4=str(random.randint(1000, 9999))
        )
        
        producer.publish(txn)
        print(f"  [{i+1}/{args.count}] Published: {txn.transaction_id} ({txn.amount} {txn.currency})")
    
    producer.flush()
    producer.close()
    print("Done!")
