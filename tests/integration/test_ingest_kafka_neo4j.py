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


    # Same accepted broker event is now followed through actual model inference,
    # native SHAP evidence and a real signed reviewer HTTP workflow. The older
    # local-case demo seeded the ledger independently; this one does not.
    import hashlib
    import secrets
    import sqlite3

    from fastapi.testclient import TestClient

    from ml.review.app import create_local_review_app
    from ml.review.auth import issue_demo_token
    from ml.training.pit_baselines import run_experiment

    artifacts = tmp_path / "frozen-synthetic-model"
    run_experiment(artifacts, count=240, seed=42)
    pinned_manifest = hashlib.sha256(
        (artifacts / "manifest.json").read_bytes()
    ).hexdigest()

    with sqlite3.connect(ledger_path) as source_connection:
        source = source_connection.execute(
            "SELECT payload_sha256 FROM transactions WHERE transaction_id=?",
            ("test-txn-identity-001",),
        ).fetchone()
        assert source is not None
        feature = source_connection.execute(
            "SELECT features_sha256 FROM transaction_feature_snapshots "
            "WHERE transaction_id=?",
            ("test-txn-identity-001",),
        ).fetchone()
        assert feature is not None

    neo4j_driver = GraphDatabase.driver(
        "bolt://localhost:7687", auth=("neo4j", "graphguard-integration-only")
    )
    try:
        with neo4j_driver.session() as session:
            graph = session.run(
                "MATCH (t:Transaction {id:$id}) "
                "RETURN t.payload_sha256 AS source_hash",
                id="test-txn-identity-001",
            ).single()
            assert graph is not None
            assert graph["source_hash"] == source[0]
    finally:
        neo4j_driver.close()

    reviewer_secret = secrets.token_urlsafe(48)
    audit_secret = secrets.token_urlsafe(48)
    app = create_local_review_app(
        ledger_path=ledger_path,
        artifact_dir=artifacts,
        expected_manifest_sha256=pinned_manifest,
        reviewer_signing_secret=reviewer_secret,
        audit_signing_secret=audit_secret,
    )
    analyst = issue_demo_token(
        reviewer_secret.encode(), subject="synthetic.analyst", role="analyst"
    )
    admin = issue_demo_token(
        reviewer_secret.encode(), subject="synthetic.admin", role="admin"
    )
    client = TestClient(app)
    unauth = client.post(
        "/cases", json={
            "transaction_id": "test-txn-identity-001",
            "request_id": "broker-case-open-001",
        },
    )
    assert unauth.status_code == 401
    opened = client.post(
        "/cases",
        headers={"Authorization": "Bearer " + analyst},
        json={
            "transaction_id": "test-txn-identity-001",
            "request_id": "broker-case-open-001",
        },
    )
    assert opened.status_code == 201, opened.text
    case = opened.json()
    assert case["status"] == "OPEN"
    assert case["version"] == 0
    assert case["evidence"]["scope"] == "SYNTHETIC_ONLY_HUMAN_REVIEW_DEMO"
    assert case["evidence"]["source_payload_sha256"] == source[0]
    assert case["evidence"]["feature_snapshot_sha256"] == feature[0]
    assert case["evidence"]["manifest_sha256"] == pinned_manifest
    assert 0 <= case["evidence"]["score"] <= 1
    cid = case["case_id"]
    explanation = client.get(
        f"/cases/{cid}/explanation",
        headers={"Authorization": "Bearer " + analyst},
    )
    assert explanation.status_code == 200, explanation.text
    assert explanation.json()["explanation_sha256"] == case["evidence"]["explanation_sha256"]
    assert explanation.json()["model_sha256"] == case["evidence"]["model_sha256"]

    escalated = client.post(
        f"/cases/{cid}/actions",
        headers={"Authorization": "Bearer " + analyst},
        json={
            "action": "escalate",
            "request_id": "broker-case-escalate-001",
            "expected_version": 0,
        },
    )
    assert escalated.status_code == 200, escalated.text
    assert escalated.json()["status"] == "ESCALATED"
    closed = client.post(
        f"/cases/{cid}/actions",
        headers={"Authorization": "Bearer " + admin},
        json={
            "action": "close_review_complete",
            "request_id": "broker-case-close-001",
            "expected_version": 1,
        },
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED_REVIEW_COMPLETE"
    assert closed.json()["version"] == 2
    assert len(closed.json()["events"]) == 3
    reloaded = client.get(
        f"/cases/{cid}", headers={"Authorization": "Bearer " + admin}
    )
    assert reloaded.status_code == 200, reloaded.text
    assert reloaded.json() == closed.json()
    with sqlite3.connect(ledger_path) as connection:
        assert connection.execute(
            "SELECT count(*) FROM transactions"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT count(*) FROM transaction_research_scores"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT count(*) FROM transaction_research_explanations"
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT count(*) FROM synthetic_review_cases"
        ).fetchone()[0] == 1

    report = {
        "scope": "same_broker_source_synthetic_human_review_only",
        "transaction_id": "test-txn-identity-001",
        "source_payload_sha256": source[0],
        "graph_source_sha256": graph["source_hash"],
        "feature_snapshot_sha256": feature[0],
        "model_manifest_sha256": pinned_manifest,
        "model_sha256": case["evidence"]["model_sha256"],
        "explanation_sha256": case["evidence"]["explanation_sha256"],
        "case_id": cid,
        "audit_head_sha256": closed.json()["audit_head_sha256"],
        "review_transitions": [
            event["action"] for event in closed.json()["events"]
        ],
        "final_status": "CLOSED_REVIEW_COMPLETE",
        "limitations": [
            "Synthetic source events only, one reviewer tenant and local SQLite.",
            "The real graph is corroborated, but the fitted model reads the independently "
            "persisted PIT source ledger; this does not prove graph-embedding inference.",
            "TestClient is signed HTTP ASGI, not an actual Chromium browser.",
            "Closing a case is a human review state, not fraud guilt.",
        ],
    }
    destination = os.getenv("GRAPHGUARD_BROKER_CASE_EVIDENCE_PATH")
    if destination:
        Path(destination).write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
    print(
        "PASS: SAME Kafka/Neo4j source → PIT model → SHAP → signed human case audit"
    )
