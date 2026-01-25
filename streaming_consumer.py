"""
GraphGuard - Streaming Consumer (Redis Streams)
===============================================
Processes transactions from Redis Streams and writes them to Neo4j.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Optional
import urllib.request
import urllib.error
import socket

import redis

try:
    import requests
except Exception:
    requests = None

from neo4j import GraphDatabase


class StreamingConsumer:
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379):
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.stream_name = "graphguard:transactions"
        self.consumer_group = "fraud-detection"
        self.consumer_name = "consumer-1"
        self.api_url = os.getenv("GRAPHGUARD_API_URL", "http://localhost:8000/score")
        self.api_key = os.getenv("API_KEY", "change-me")
        self.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD", "graphguard_dev")
        self.neo4j_driver = None

        # Create consumer group if not exists
        try:
            self.redis_client.xgroup_create(
                self.stream_name,
                self.consumer_group,
                id="0",
                mkstream=True
            )
            print(f"Created consumer group: {self.consumer_group}")
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

        self._init_neo4j()

    def _init_neo4j(self) -> None:
        """Initialize Neo4j connection for live graph updates."""
        try:
            self.neo4j_driver = GraphDatabase.driver(
                self.neo4j_uri,
                auth=(self.neo4j_user, self.neo4j_password)
            )
            self.neo4j_driver.verify_connectivity()
            self._create_indexes()
            print("Neo4j connected for live updates")
        except Exception as exc:
            self.neo4j_driver = None
            print(f"Neo4j not available for live updates: {exc}")

    def _create_indexes(self) -> None:
        if not self.neo4j_driver:
            return
        with self.neo4j_driver.session() as session:
            session.run("CREATE INDEX user_id_index IF NOT EXISTS FOR (u:User) ON (u.id)")
            session.run("CREATE INDEX merchant_id_index IF NOT EXISTS FOR (m:Merchant) ON (m.id)")
            session.run("CREATE INDEX device_id_index IF NOT EXISTS FOR (d:Device) ON (d.id)")
            session.run("CREATE INDEX txn_id_index IF NOT EXISTS FOR (t:Transaction) ON (t.id)")
            session.run("CREATE INDEX txn_timestamp_index IF NOT EXISTS FOR (t:Transaction) ON (t.timestamp)")

    def _parse_timestamp(self, value) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            timestamp = value / 1000 if value > 1e12 else value
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        if isinstance(value, str):
            try:
                cleaned = value.replace("Z", "+00:00")
                return datetime.fromisoformat(cleaned)
            except ValueError:
                pass
        return datetime.now(tz=timezone.utc)

    def _heuristic_score(self, transaction: dict) -> float:
        if transaction.get("is_fraud") is True:
            return 0.92
        amount = float(transaction.get("amount") or 0.0)
        if amount >= 2500:
            return 0.9
        if amount >= 1000:
            return 0.75
        if amount >= 300:
            return 0.55
        return 0.1

    def _decision_from_score(self, fraud_score: float) -> str:
        if fraud_score < 0.3:
            return "AUTO_APPROVE"
        if fraud_score < 0.7:
            return "REVIEW"
        return "AUTO_DECLINE"

    def _status_from_decision(self, decision: str) -> str:
        if decision == "AUTO_DECLINE":
            return "PENDING"
        if decision == "REVIEW":
            return "IN_REVIEW"
        return "RESOLVED_LEGITIMATE"

    def _post_json(self, payload: dict, headers: dict, timeout: int = 2) -> Optional[dict]:
        if requests is not None:
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=timeout
                )
                if response.status_code == 200:
                    return response.json()
                print(f"API error: {response.status_code}")
                return None
            except requests.exceptions.ConnectionError:
                print("API not running")
                return None
            except Exception as exc:
                print(f"API error: {exc}")
                return None

        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.api_url,
            data=data,
            headers={**headers, "Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    print(f"API error: {response.status}")
                    return None
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            print(f"API error: {exc.code}")
            return None
        except (urllib.error.URLError, socket.timeout) as exc:
            print(f"API not running: {exc}")
            return None
        except Exception as exc:
            print(f"API error: {exc}")
            return None

    def _write_to_neo4j(self, transaction: dict, fraud_score: float, decision: str) -> None:
        if not self.neo4j_driver:
            return

        timestamp = self._parse_timestamp(transaction.get("timestamp"))
        status = self._status_from_decision(decision)
        params = {
            "transaction_id": transaction.get("transaction_id"),
            "user_id": transaction.get("user_id"),
            "merchant_id": transaction.get("merchant_id"),
            "device_id": transaction.get("device_id"),
            "amount": float(transaction.get("amount") or 0.0),
            "currency": transaction.get("currency", "USD"),
            "timestamp": timestamp,
            "fraud_score": float(fraud_score),
            "status": status,
            "ip_address": transaction.get("ip_address", ""),
        }

        cypher = """
        MERGE (u:User {id: $user_id})
        ON CREATE SET u.created_at = datetime()

        MERGE (m:Merchant {id: $merchant_id})
        ON CREATE SET m.created_at = datetime(),
                      m.name = $merchant_id

        MERGE (d:Device {id: $device_id})
        ON CREATE SET d.first_seen = $timestamp
        SET d.last_seen = $timestamp

        MERGE (t:Transaction {id: $transaction_id})
        ON CREATE SET t.amount = $amount,
                      t.timestamp = $timestamp,
                      t.currency = $currency,
                      t.fraud_score = $fraud_score,
                      t.status = $status,
                      t.ip_address = $ip_address,
                      t.user_id = $user_id,
                      t.merchant_id = $merchant_id,
                      t.device_id = $device_id
        ON MATCH SET t.amount = $amount,
                     t.timestamp = $timestamp,
                     t.currency = $currency,
                     t.fraud_score = $fraud_score,
                     t.status = $status,
                     t.ip_address = $ip_address

        MERGE (u)-[:PERFORMED]->(t)
        MERGE (t)-[:PAID_TO]->(m)
        MERGE (t)-[:USED_DEVICE]->(d)
        """

        try:
            with self.neo4j_driver.session() as session:
                session.run(cypher, params)
        except Exception as exc:
            print(f"Neo4j write failed: {exc}")

    def process_transaction(self, transaction: dict):
        """Send transaction to fraud detection API and persist into Neo4j."""
        try:
            if self.api_key == "change-me":
                print("API_KEY not set. Update your environment or .env file.")
            headers = {"X-API-Key": self.api_key}
            result = self._post_json(transaction, headers)
            if result is None:
                fraud_score = self._heuristic_score(transaction)
                decision = self._decision_from_score(fraud_score)
            else:
                fraud_score = float(result.get("fraud_score") or 0.0)
                decision = result.get("decision") or self._decision_from_score(fraud_score)
                if result.get("model_version") == "unknown":
                    fraud_score = self._heuristic_score(transaction)
                    decision = self._decision_from_score(fraud_score)

            self._write_to_neo4j(transaction, fraud_score, decision)

            return {
                "fraud_score": fraud_score,
                "decision": decision
            }

        except Exception as exc:
            print(f"Error: {exc}")
            return None

    def consume_messages(self):
        """Consume and process messages from stream."""
        print(f"\nListening to stream: {self.stream_name}")
        print(f"Consumer group: {self.consumer_group}")
        print("Processing transactions... (Press Ctrl+C to stop)\n")

        processed = 0
        last_id = ">"

        try:
            while True:
                messages = self.redis_client.xreadgroup(
                    self.consumer_group,
                    self.consumer_name,
                    {self.stream_name: last_id},
                    count=1,
                    block=1000
                )

                if not messages:
                    continue

                for _, message_list in messages:
                    for message_id, message_data in message_list:
                        txn_json = message_data.get("data", "{}")
                        transaction = json.loads(txn_json)

                        processed += 1
                        print(f"\nMessage #{processed}: {transaction.get('transaction_id')}")
                        print(f"  Amount: ${transaction.get('amount')}")

                        result = self.process_transaction(transaction)
                        if result:
                            score = result["fraud_score"]
                            decision = result["decision"]
                            print(f"  Score: {score:.3f} | Decision: {decision}")

                        self.redis_client.xack(
                            self.stream_name,
                            self.consumer_group,
                            message_id
                        )
        except KeyboardInterrupt:
            print(f"\nStopped. Processed {processed} transactions.")
        except Exception as exc:
            print(f"\nError: {exc}")
            time.sleep(1)
        finally:
            self.close()

    def close(self) -> None:
        if self.neo4j_driver:
            self.neo4j_driver.close()


def main():
    print("=" * 60)
    print("GraphGuard Streaming Consumer (Redis Streams)")
    print("=" * 60)

    try:
        consumer = StreamingConsumer()
        consumer.consume_messages()
    except redis.ConnectionError:
        print("\nCannot connect to Redis. Make sure Redis is running:")
        print("  docker-compose up -d redis")
    except Exception as exc:
        print(f"\nError: {exc}")


if __name__ == "__main__":
    main()
