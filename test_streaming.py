"""
GraphGuard - Streaming Pipeline Demo
====================================
Quick test of the streaming setup
"""

import time
import subprocess
import sys

def main():
    print("\n" + "="*60)
    print("GraphGuard Streaming Pipeline Demo")
    print("="*60)
    
    print("\n📋 This demo will:")
    print("  1. Start a consumer (fraud detection processor)")
    print("  2. Generate 10 sample transactions")
    print("  3. Show real-time fraud scoring")
    
    input("\nPress Enter to start...")
    
    print("\n🚀 Starting consumer in background...")
    
    # Start consumer in background
    consumer_process = subprocess.Popen(
        [sys.executable, 'streaming_consumer.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give consumer time to start
    time.sleep(2)
    
    print("✅ Consumer started")
    print("\n📤 Generating transactions...\n")
    
    # Import producer
    from streaming_producer import StreamingProducer
    
    producer = StreamingProducer()
    
    # Generate 10 transactions
    for i in range(10):
        txn = producer.generate_sample_transaction()
        msg_id = producer.publish_transaction(txn)
        print(f"✅ Published {i+1}/10: {txn['transaction_id']} | ${txn['amount']}")
        time.sleep(0.5)
    
    print("\n✅ All transactions published!")
    print("\nWaiting for processing to complete...")
    time.sleep(3)
    
    # Stop consumer
    consumer_process.terminate()
    
    print("\n" + "="*60)
    print("Demo Complete!")
    print("="*60)
    print("\n📊 Summary:")
    print("  • Published: 10 transactions")
    print("  • Processed: Via streaming pipeline")
    print("  • Scored: Real-time fraud detection")
    
    print("\n🎯 To run full streaming:")
    print("  Terminal 1: python streaming_consumer.py")
    print("  Terminal 2: python streaming_producer.py")


if __name__ == '__main__':
    main()
