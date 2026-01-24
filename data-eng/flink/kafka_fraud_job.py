#!/usr/bin/env python
"""
GraphGuard - Apache Flink Kafka Consumer Job
==============================================
File: data-eng/flink/kafka_fraud_job.py
Reference: Specification.md Lines 826-836

Executable Flink job that consumes transactions from Kafka,
runs pattern detection, and publishes alerts.

Usage:
    # Local testing
    python kafka_fraud_job.py --mode local
    
    # Submit to Flink cluster
    flink run -py kafka_fraud_job.py --mode cluster
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Optional

import structlog

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from data_eng.flink.fraud_patterns import FraudPatternEngine, PatternAlert
from data_eng.flink.validators import validate_transaction

logger = structlog.get_logger(__name__)


# ============================================
# Configuration
# ============================================

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
INPUT_TOPIC = os.getenv('KAFKA_INPUT_TOPIC', 'transactions.raw')
OUTPUT_TOPIC = os.getenv('KAFKA_OUTPUT_TOPIC', 'fraud.patterns')
CONSUMER_GROUP = os.getenv('KAFKA_CONSUMER_GROUP', 'graphguard-flink-patterns')


# ============================================
# Job Modes
# ============================================

def run_local_mode():
    """
    Run pattern detection in local mode (without Flink cluster).
    Uses confluent-kafka consumer directly for testing.
    """
    try:
        from confluent_kafka import Consumer, Producer, KafkaError
    except ImportError:
        logger.error("confluent-kafka not installed. Run: pip install confluent-kafka")
        sys.exit(1)
    
    # Consumer configuration
    consumer_config = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': CONSUMER_GROUP,
        'auto.offset.reset': 'latest',
        'enable.auto.commit': True,
    }
    
    # Producer configuration
    producer_config = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    }
    
    consumer = Consumer(consumer_config)
    producer = Producer(producer_config)
    engine = FraudPatternEngine()
    
    consumer.subscribe([INPUT_TOPIC])
    logger.info("Started local consumer", topic=INPUT_TOPIC, group=CONSUMER_GROUP)
    
    try:
        processed = 0
        alerts_generated = 0
        
        while True:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                logger.error("Kafka error", error=msg.error())
                continue
            
            # Parse transaction
            try:
                transaction = json.loads(msg.value().decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.warning("Invalid JSON in message", error=str(e))
                continue
            
            # Validate
            validation = validate_transaction(transaction)
            if not validation.is_valid:
                logger.warning("Invalid transaction", errors=validation.errors)
                continue
            
            # Process through pattern engine
            timestamp_ms = msg.timestamp()[1] if msg.timestamp()[0] == 1 else None
            alerts = engine.process_transaction(
                validation.sanitized_data,
                timestamp_ms=timestamp_ms,
                validate=False  # Already validated
            )
            
            processed += 1
            
            # Publish alerts
            for alert in alerts:
                alert_json = json.dumps({
                    'pattern_type': alert.pattern_type,
                    'user_id': alert.user_id,
                    'risk_score': alert.risk_score,
                    'timestamp': alert.timestamp.isoformat(),
                    'details': alert.details
                })
                
                producer.produce(
                    OUTPUT_TOPIC,
                    key=alert.user_id.encode('utf-8'),
                    value=alert_json.encode('utf-8')
                )
                alerts_generated += 1
                
                logger.info(
                    "Alert generated",
                    pattern=alert.pattern_type,
                    user_id=alert.user_id,
                    risk_score=alert.risk_score
                )
            
            # Periodic flush and stats
            if processed % 100 == 0:
                producer.flush()
                logger.info(
                    "Progress",
                    processed=processed,
                    alerts=alerts_generated,
                    stats=engine.get_stats()
                )
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        consumer.close()
        producer.flush()
        logger.info(
            "Final stats",
            processed=processed,
            alerts=alerts_generated,
            engine_stats=engine.get_stats()
        )


def run_flink_mode():
    """
    Run as PyFlink streaming job on Flink cluster.
    Requires PyFlink to be installed and configured.
    """
    try:
        from pyflink.datastream import StreamExecutionEnvironment
        from pyflink.datastream.connectors.kafka import (
            FlinkKafkaConsumer,
            FlinkKafkaProducer
        )
        from pyflink.common.serialization import SimpleStringSchema
        from pyflink.datastream.functions import MapFunction, ProcessFunction
        from pyflink.common.typeinfo import Types
    except ImportError:
        logger.error("PyFlink not installed. Run: pip install apache-flink")
        sys.exit(1)
    
    # Create execution environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(4)
    
    # Enable checkpointing (every 60 seconds)
    env.enable_checkpointing(60000)
    
    # Kafka properties
    kafka_props = {
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': CONSUMER_GROUP,
    }
    
    # Kafka source
    kafka_consumer = FlinkKafkaConsumer(
        topics=INPUT_TOPIC,
        deserialization_schema=SimpleStringSchema(),
        properties=kafka_props
    )
    kafka_consumer.set_start_from_latest()
    
    # Create stream
    transactions = env.add_source(kafka_consumer)
    
    # Pattern detection function
    class PatternDetectorFunction(ProcessFunction):
        def __init__(self):
            self.engine = None
        
        def open(self, runtime_context):
            self.engine = FraudPatternEngine()
        
        def process_element(self, value, ctx):
            try:
                transaction = json.loads(value)
                
                # Validate
                validation = validate_transaction(transaction)
                if not validation.is_valid:
                    return
                
                # Get event time
                timestamp_ms = ctx.timestamp() or int(datetime.now().timestamp() * 1000)
                
                # Process
                alerts = self.engine.process_transaction(
                    validation.sanitized_data,
                    timestamp_ms=timestamp_ms,
                    validate=False
                )
                
                # Yield alerts
                for alert in alerts:
                    yield json.dumps({
                        'pattern_type': alert.pattern_type,
                        'user_id': alert.user_id,
                        'risk_score': alert.risk_score,
                        'timestamp': alert.timestamp.isoformat(),
                        'details': alert.details
                    })
            
            except Exception as e:
                logger.error("Error processing transaction", error=str(e))
    
    # Apply pattern detection
    patterns = transactions.process(PatternDetectorFunction(), output_type=Types.STRING())
    
    # Kafka sink
    kafka_producer = FlinkKafkaProducer(
        topic=OUTPUT_TOPIC,
        serialization_schema=SimpleStringSchema(),
        producer_config={'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS}
    )
    
    patterns.add_sink(kafka_producer)
    
    # Execute job
    logger.info("Starting Flink job", job_name="GraphGuard Fraud Pattern Detection")
    env.execute("GraphGuard Fraud Pattern Detection")


# ============================================
# Entry Point
# ============================================

def main():
    parser = argparse.ArgumentParser(description="GraphGuard Flink Pattern Detection Job")
    parser.add_argument(
        '--mode',
        choices=['local', 'cluster'],
        default='local',
        help='Execution mode: local (confluent-kafka) or cluster (PyFlink)'
    )
    args = parser.parse_args()
    
    if args.mode == 'local':
        run_local_mode()
    else:
        run_flink_mode()


if __name__ == "__main__":
    main()
