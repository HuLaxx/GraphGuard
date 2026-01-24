"""
GraphGuard - PyFlink Fraud Detection Job
=========================================
File: data-eng/flink/job.py

Goal: Run the FraudPatternEngine on a Flink cluster.
"""

import os
import json
import logging
import sys

# Import Flink dependencies
from pyflink.common import WatermarkStrategy, Encoder, Types
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream import StreamExecutionEnvironment, RuntimeContext, KeyedProcessFunction
from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer, FlinkKafkaProducer
from pyflink.datastream.connectors.file_system import FileSink, OutputFileConfig, RollingPolicy

# Add parent directory to path to import fraud_patterns
# In a real cluster, you'd package this with --pyFiles
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flink.fraud_patterns import FraudPatternEngine

class FraudDetectorFunction(KeyedProcessFunction):
    """
    Wraps the FraudPatternEngine in a Flink KeyedProcessFunction.
    """
    def __init__(self):
        self.engine = None
    
    def open(self, runtime_context: RuntimeContext):
        # Initialize engine per slot
        # Note: In a real prod job, we would use Flink State (ValueState) here
        # instead of the python dicts inside the engine.
        # For this phase, we wrap the existing logic.
        self.engine = FraudPatternEngine()
    
    def process_element(self, value, ctx: KeyedProcessFunction.Context, out):
        try:
            transaction = json.loads(value)
            
            # The engine logic is "per user" mostly, but some parts are global (device)
            # Since we keyBy(user_id), generic "new device" checks might be split across slots.
            # However, for a demo hardening, this is acceptable parallelization.
            
            alerts = self.engine.process_transaction(transaction)
            
            for alert in alerts:
                # Emit alert as JSON string
                alert_dict = {
                    "pattern_type": alert.pattern_type,
                    "user_id": alert.user_id,
                    "risk_score": alert.risk_score,
                    "timestamp": alert.timestamp.isoformat(),
                    "details": alert.details
                }
                out.collect(json.dumps(alert_dict))
                
        except Exception as e:
            logging.error(f"Error processing transaction: {e}")

def run():
    # 1. Setup Environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2) # Matches docker-compose taskmanager config
    
    # Checkpointing
    env.enable_checkpointing(60000) # 1 minute

    # 2. Define Source (Kafka)
    kafka_props = {
        'bootstrap.servers': 'kafka:29092', # Internal docker network
        'group.id': 'flink-fraud-detector',
        'auto.offset.reset': 'latest'
    }
    
    kafka_source = FlinkKafkaConsumer(
        topics='transactions.raw',
        deserialization_schema=SimpleStringSchema(),
        properties=kafka_props
    )
    
    # 3. Define Stream
    ds = env.add_source(kafka_source)
    
    # 4. Process
    # Key by user_id to ensure user-centric patterns (RapidFire, Velocity) are local
    alerts = ds \
        .key_by(lambda s: json.loads(s).get('user_id', 'unknown')) \
        .process(FraudDetectorFunction())
    
    # 5. Define Sink (Kafka)
    kafka_sink = FlinkKafkaProducer(
        topic='fraud.patterns',
        serialization_schema=SimpleStringSchema(),
        producer_config={'bootstrap.servers': 'kafka:29092'}
    )
    
    alerts.add_sink(kafka_sink)
    
    # 6. Execute
    env.execute("GraphGuard Fraud Detection Job")

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")
    run()
