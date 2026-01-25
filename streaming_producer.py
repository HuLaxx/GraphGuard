"""
GraphGuard - Streaming Producer (Redis Streams)
===============================================
Lightweight alternative to Kafka using Redis Streams.
"""

import argparse
import json
import random
import time
from datetime import datetime

import redis


class StreamingProducer:
    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        users: int = 5000,
        merchants: int = 500,
        devices: int = 3000,
        min_amount: float = 10.0,
        max_amount: float = 5000.0,
        fraud_rate: float = 0.08,
    ):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.stream_name = "graphguard:transactions"
        self.users = users
        self.merchants = merchants
        self.devices = devices
        self.min_amount = min_amount
        self.max_amount = max_amount
        self.fraud_rate = fraud_rate

    def publish_transaction(self, transaction: dict):
        """Publish transaction to Redis stream."""
        if "timestamp" not in transaction:
            transaction["timestamp"] = datetime.now().isoformat()

        message_id = self.redis_client.xadd(
            self.stream_name,
            {"data": json.dumps(transaction)}
        )
        return message_id

    def generate_sample_transaction(self) -> dict:
        """Generate a sample transaction."""
        is_fraud = random.random() < self.fraud_rate
        if is_fraud:
            amount = round(random.uniform(self.max_amount * 0.6, self.max_amount * 1.8), 2)
        else:
            amount = round(random.uniform(self.min_amount, self.max_amount), 2)

        transaction = {
            "transaction_id": f"txn_{int(time.time() * 1000)}",
            "user_id": f"user_{random.randint(1, self.users):05d}",
            "merchant_id": f"merchant_{random.randint(1, self.merchants):04d}",
            "amount": amount,
            "currency": "USD",
            "device_id": f"device_{random.randint(1, self.devices):04d}",
            "ip_address": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
            "card_last4": f"{random.randint(0, 9999):04d}",
            "timestamp": datetime.now().isoformat(),
            "is_fraud": is_fraud,
        }
        return transaction


def main():
    parser = argparse.ArgumentParser(description="GraphGuard Streaming Producer (Redis Streams)")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between transactions")
    parser.add_argument("--count", type=int, default=0, help="Number of transactions to send (0 = infinite)")
    parser.add_argument("--min-amount", type=float, default=10.0)
    parser.add_argument("--max-amount", type=float, default=5000.0)
    parser.add_argument("--fraud-rate", type=float, default=0.08, help="Probability of a transaction marked as fraud")
    parser.add_argument("--users", type=int, default=5000)
    parser.add_argument("--merchants", type=int, default=500)
    parser.add_argument("--devices", type=int, default=3000)
    args = parser.parse_args()

    print("=" * 60)
    print("GraphGuard Streaming Producer (Redis Streams)")
    print("=" * 60)

    try:
        producer = StreamingProducer(
            users=args.users,
            merchants=args.merchants,
            devices=args.devices,
            min_amount=args.min_amount,
            max_amount=args.max_amount,
            fraud_rate=args.fraud_rate,
        )

        print("Connected to Redis")
        print(f"Publishing to stream: {producer.stream_name}")
        print("Generating transactions... (Press Ctrl+C to stop)\n")

        count = 0
        while True:
            if args.count and count >= args.count:
                break

            txn = producer.generate_sample_transaction()
            msg_id = producer.publish_transaction(txn)
            count += 1

            tag = "FRAUD" if txn["is_fraud"] else "OK"
            print(f"Published #{count}: {txn['transaction_id']} | ${txn['amount']} | {tag} | {msg_id}")

            time.sleep(max(0.1, args.interval))

        print(f"\nStopped. Published {count} transactions.")

    except KeyboardInterrupt:
        print(f"\nStopped. Published {count} transactions.")
    except redis.ConnectionError:
        print("\nCannot connect to Redis. Make sure Redis is running:")
        print("  docker-compose up -d redis")
    except Exception as exc:
        print(f"\nError: {exc}")


if __name__ == "__main__":
    main()
