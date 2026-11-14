"""Opt-in broker-backed GraphGuard acceptance, using disposable Kafka + Neo4j.

Run with GRAPHGUARD_INGESTION_INTEGRATION=1. No provider credentials required.
This checks ONLY ingestion and graph projection, not ML/SHAP/case management.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid

import pytest

if os.getenv("GRAPHGUARD_INGESTION_INTEGRATION") != "1":
    pytest.skip("Set GRAPHGUARD_INGESTION_INTEGRATION=1 with disposable services", allow_module_level=True)

from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic
from neo4j import GraphDatabase

CONSUMER_DIR = Path(__file__).resolve().parents[2] / "data-eng" / "consumers"
sys.path.insert(0, str(CONSUMER_DIR))
spec = importlib.util.spec_from_file_location("graphguard_integration_builder", CONSUMER_DIR / "graph_builder.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
GraphBuilder = module.GraphBuilder


def synthetic_event(amount=17.25):
    return {
        "transaction_id": "test-txn-identity-001",
        "user_id": "synthetic-reviewer-001",
        "merchant_id": "synthetic-merchant-001",
        "device_id": "synthetic-device-001",
        "amount": amount,
        "currency": "GBP",
        "timestamp": 1790000000000,
        "idempotency_key": "a" * 64,
        "schema_version": 1,
    }


def publish_events():
    admin = AdminClient({"bootstrap.servers": "127.0.0.1:9092"})
    for topic in ("transactions.raw", "transactions.dlq"):
        futures = admin.create_topics([NewTopic(topic, num_partitions=1, replication_factor=1)])
        for name, future in futures.items():
            try:
                future.result(timeout=30)
            except Exception as exc:
                if "TOPIC_ALREADY_EXISTS" not in str(exc):
                    raise
    events = [
        synthetic_event(),
        synthetic_event(),  # identical retry must not create another graph transaction
        synthetic_event(999.0),  # same ID with different content -> conflict DLQ
        {"transaction_id": "bad-transaction"},  # invalid -> DLQ
    ]
    producer = Producer({"bootstrap.servers": "127.0.0.1:9092", "acks": "all"})
    errors = []

    def delivered(err, _msg):
        if err:
            errors.append(str(err))

    for event in events:
        producer.produce("transactions.raw", key=b"synthetic-txn-identity", value=json.dumps(event).encode(), on_delivery=delivered)
    assert producer.flush(30) == 0
    assert not errors


def run_consumer(group_id: str, ledger_path: Path, monkeypatch):
    monkeypatch.setenv("GRAPHGUARD_LEDGER_PATH", str(ledger_path))
    monkeypatch.setenv("GRAPHGUARD_JSON_FIXTURE_MODE", "true")
    builder = GraphBuilder(
        consumer_config={
            "bootstrap.servers": "127.0.0.1:9092",
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        },
        neo4j_config={"uri": "bolt://localhost:7687", "user": "neo4j", "password": "graphguard-integration-only"},
    )
    # Explicitly opt into JSON fixtures, not a silent fallback after Avro failure.
    builder.avro_deserializer = None
    builder.BATCH_SIZE = 1
    builder.run(max_messages=4)


def verify_graph():
    driver = GraphDatabase.driver(
        "bolt://localhost:7687", auth=("neo4j", "graphguard-integration-only")
    )
    try:
        with driver.session() as session:
            record = session.run(
                """MATCH (u:User)-[:PERFORMED]->(t:Transaction)-[:PAID_TO]->(m:Merchant)
                   MATCH (t)-[:USED_DEVICE]->(d:Device)
                   WHERE t.id = $id
                   RETURN t.amount AS amount, t.payload_sha256 AS digest,
                          u.id AS user_id, m.id AS merchant_id, d.id AS device_id""",
                id="test-txn-identity-001",
            ).single()
            assert record is not None
            assert record["amount"] == 17.25
            assert len(record["digest"]) == 64
            assert record["user_id"] == "synthetic-reviewer-001"
            assert record["merchant_id"] == "synthetic-merchant-001"
            assert record["device_id"] == "synthetic-device-001"
            assert session.run(
                "MATCH (t:Transaction {id: $id}) RETURN count(t) AS n",
                id="test-txn-identity-001",
            ).single()["n"] == 1
    finally:
        driver.close()


def test_kafka_ledger_neo4j_conflict_and_restart_replay(tmp_path, monkeypatch):
    from transaction_ledger import TransactionLedger

    publish_events()
    ledger_path = tmp_path / "durable-source.sqlite3"
    run_consumer("graphguard-integration-first-" + uuid.uuid4().hex, ledger_path, monkeypatch)
    verify_graph()

    ledger = TransactionLedger(str(ledger_path))
    assert ledger.connection.execute("SELECT count(*) FROM transactions").fetchone()[0] == 1
    assert ledger.connection.execute("SELECT count(*) FROM transaction_conflicts").fetchone()[0] == 1
    ledger.close()

    # Different group intentionally replays the same broker events after restart.
    run_consumer("graphguard-integration-replay-" + uuid.uuid4().hex, ledger_path, monkeypatch)
    verify_graph()
    ledger = TransactionLedger(str(ledger_path))
    assert ledger.connection.execute("SELECT count(*) FROM transactions").fetchone()[0] == 1
    assert ledger.connection.execute("SELECT count(*) FROM transaction_conflicts").fetchone()[0] == 1
    ledger.close()

    dlq = Consumer({
        "bootstrap.servers": "127.0.0.1:9092",
        "group.id": "graphguard-integration-dlq-" + uuid.uuid4().hex,
        "auto.offset.reset": "earliest",
    })
    try:
        dlq.subscribe(["transactions.dlq"])
        reasons = []
        # There may be four DLQs after two group replays; inspect at least the first two.
        import time
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and len(reasons) < 2:
            msg = dlq.poll(1)
            if msg is not None and msg.error() is None:
                headers = dict(msg.headers() or [])
                reasons.append(headers["error"].decode())
        assert any("TransactionIdConflict" in reason for reason in reasons)
        assert any("InvalidTransaction" in reason for reason in reasons)
    finally:
        dlq.close()
