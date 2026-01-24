"""
GraphGuard - Streaming Consumer (Redis Streams)
===============================================
Processes transactions from Redis Streams
"""

import redis
import json
import time
import requests

class StreamingConsumer:
    def __init__(self, redis_host='localhost', redis_port=6379):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.stream_name = 'graphguard:transactions'
        self.consumer_group = 'fraud-detection'
        self.consumer_name = 'consumer-1'
        self.api_url = 'http://localhost:8000/score'
        self.api_key = 'gguard_dev_key_9x7k2p4m1n8q6r5t3w0z'
        
        # Create consumer group if not exists
        try:
            self.redis_client.xgroup_create(
                self.stream_name,
                self.consumer_group,
                id='0',
                mkstream=True
            )
            print(f"✅ Created consumer group: {self.consumer_group}")
        except redis.ResponseError as e:
            if 'BUSYGROUP' not in str(e):
                raise
    
    def process_transaction(self, transaction: dict):
        """Send transaction to fraud detection API"""
        try:
            headers = {'X-API-Key': self.api_key}
            response = requests.post(
                self.api_url,
                json=transaction,
                headers=headers,
                timeout=2
            )
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                print(f"   ⚠️  API error: {response.status_code}")
                return None
                
        except requests.exceptions.ConnectionError:
            print("   ⚠️  API not running")
            return None
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
            return None
    
    def consume_messages(self):
        """Consume and process messages from stream"""
        print(f"\n📥 Listening to stream: {self.stream_name}")
        print(f"👥 Consumer group: {self.consumer_group}")
        print(f"🔄 Processing transactions... (Press Ctrl+C to stop)\n")
        
        processed = 0
        last_id = '>'
        
        while True:
            try:
                # Read from stream
                messages = self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_name: last_id},
                    count=1,
                    block=1000  # Block for 1 second
                )
                
                if not messages:
                    continue
                
                for stream_name, message_list in messages:
                    for message_id, message_data in message_list:
                        # Parse transaction
                        txn_json = message_data.get('data', '{}')
                        transaction = json.loads(txn_json)
                        
                        processed += 1
                        print(f"\n📨 Message #{processed}: {transaction.get('transaction_id')}")
                        print(f"   Amount: ${transaction.get('amount')}")
                        
                        # Process with fraud detection API
                        result = self.process_transaction(transaction)
                        
                        if result:
                            score = result['fraud_score']
                            decision = result['decision']
                            
                            # Color-code output
                            if decision == 'AUTO_APPROVE':
                                icon = '✅'
                            elif decision == 'REVIEW':
                                icon = '⚠️ '
                            else:
                                icon = '❌'
                            
                            print(f"   {icon} Score: {score:.3f} | Decision: {decision}")
                        
                        # Acknowledge message
                        self.redis_client.xack(
                            self.stream_name,
                            self.consumer_group,
                            message_id
                        )
                        
            except KeyboardInterrupt:
                print(f"\n\n✅ Stopped. Processed {processed} transactions.")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                time.sleep(1)


def main():
    print("="*60)
    print("GraphGuard Streaming Consumer (Redis Streams)")
    print("="*60)
    
    try:
        consumer = StreamingConsumer()
        consumer.consume_messages()
        
    except redis.ConnectionError:
        print("\n❌ Cannot connect to Redis. Make sure Redis is running:")
        print("   docker-compose up -d redis")
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == '__main__':
    main()
