"""
GraphGuard - Streaming Producer (Redis Streams)
===============================================
Lightweight alternative to Kafka using Redis Streams
"""

import redis
import json
import time
from datetime import datetime
import random

class StreamingProducer:
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.stream_name = 'graphguard:transactions'
        
    def publish_transaction(self, transaction: dict):
        """Publish transaction to Redis stream"""
        # Add timestamp if not present
        if 'timestamp' not in transaction:
            transaction['timestamp'] = datetime.now().isoformat()
        
        # Publish to stream
        message_id = self.redis_client.xadd(
            self.stream_name,
            {'data': json.dumps(transaction)}
        )
        
        return message_id
    
    def generate_sample_transaction(self):
        """Generate a sample transaction"""
        transaction = {
            'transaction_id': f'txn_{int(time.time() * 1000)}',
            'user_id': f'user_{random.randint(1, 5000):05d}',
            'merchant_id': f'merchant_{random.randint(1, 500):04d}',
            'amount': round(random.uniform(10, 5000), 2),
            'currency': 'USD',
            'device_id': f'device_{random.randint(1, 3000):04d}',
            'ip_address': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'timestamp': datetime.now().isoformat()
        }
        return transaction


def main():
    print("="*60)
    print("GraphGuard Streaming Producer (Redis Streams)")
    print("="*60)
    
    try:
        producer = StreamingProducer()
        
        print("\n✅ Connected to Redis")
        print(f"📤 Publishing to stream: {producer.stream_name}")
        print("\nGenerating transactions... (Press Ctrl+C to stop)\n")
        
        count = 0
        while True:
            # Generate transaction
            txn = producer.generate_sample_transaction()
            
            # Publish
            msg_id = producer.publish_transaction(txn)
            count += 1
            
            # Display
            print(f"✅ Published #{count}: {txn['transaction_id']} | ${txn['amount']} | {msg_id}")
            
            # Wait before next transaction
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\n\n✅ Stopped. Published {count} transactions.")
    except redis.ConnectionError:
        print("\n❌ Cannot connect to Redis. Make sure Redis is running:")
        print("   docker-compose up -d redis")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == '__main__':
    main()
