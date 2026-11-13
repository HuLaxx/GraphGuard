"""Real Schema Registry + Avro producer -> Kafka -> ledger -> Neo4j acceptance.

This suite uses disposable, local Docker services and synthetic identities only.
No bank users, live payments, model scoring or commercial deployment are involved.
Run when GRAPHGUARD_INGESTION_INTEGRATION=1.
"""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from urllib.request import urlopen
import uuid

import pytest

if os.getenv("GRAPHGUARD_INGESTION_INTEGRATION") != "1":
    pytest.skip("Requires disposable Kafka + Neo4j + Schema Registry", allow_module_level=True)

from confluent_kafka import Consumer
from confluent_kafka.admin import AdminClient, NewTopic
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[2]
CONSUMERS = ROOT / "data-eng" / "consumers"
PRODUCERS = ROOT / "data-eng" / "producers"
sys.path.insert(0, str(CONSUMERS))
sys.path.insert(0, str(PRODUCERS))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


producer_module = load_module("graphguard_actual_avro_producer", PRODUCERS / "transaction_ingester.py")
builder_module = load_module("graphguard_actual_avro_builder", CONSUMERS / "graph_builder.py")
TransactionEvent = producer_module.TransactionEvent
TransactionProducer = producer_module.TransactionProducer
GraphBuilder = builder_module.GraphBuilder

KAFKA_URL = "localhost:9092"
REGISTRY_URL = "http://127.0.0.1:8082"
NEO4J_URL = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "graphguard-integration-only")


class AvroProducer(TransactionProducer):
    TOPIC = "transactions.avro.acceptance"


class AvroBuilder(GraphBuilder):
    TOPIC = AvroProducer.TOPIC
    DLQ_TOPIC = "transactions.avro.acceptance.dlq"


class OutageProducer(TransactionProducer):
    TOPIC = "transactions.avro.registry-outage"


class OutageBuilder(GraphBuilder):
    TOPIC = OutageProducer.TOPIC
    DLQ_TOPIC = "transactions.avro.registry-outage.dlq"


def create_topics(*topics):
    admin = AdminClient({"bootstrap.servers": KAFKA_URL})
    futures = admin.create_topics([NewTopic(topic, num_partitions=1, replication_factor=1) for topic in topics])
    for topic, future in futures.items():
        try:
            future.result(timeout=30)
        except Exception as exc:
            if "TOPIC_ALREADY_EXISTS" not in str(exc):
                raise


def make_event(event_id, amount=17.25):
    return TransactionEvent(
        transaction_id=event_id,
        user_id="synthetic-avro-user",
        merchant_id="synthetic-avro-merchant",
        device_id="synthetic-avro-device",
        amount=amount,
        currency="GBP",
        timestamp=datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc),
        ip_address="192.0.2.10",
        card_last4="1234",
    )


def publish(producer_type, events):
    producer = producer_type(
        producer_config={"bootstrap.servers": KAFKA_URL, "acks": "all", "enable.idempotence": True},
        schema_registry_config={"url": REGISTRY_URL},
    )
    delivered = []

    def callback(err, message):
        delivered.append((err, message.offset()))

    try:
        for event in events:
            producer.publish(event, on_delivery=callback)
        assert producer.flush(timeout=30) == 0, "Kafka delivery did not complete"
        assert len(delivered) == len(events)
        assert all(err is None for err, _ in delivered), delivered
    finally:
        producer.close()


def start_builder(builder_type, group, ledger_path, monkeypatch, *, registry_url=REGISTRY_URL):
    monkeypatch.setenv("GRAPHGUARD_JSON_FIXTURE_MODE", "false")
    monkeypatch.setenv("GRAPHGUARD_LEDGER_PATH", str(ledger_path))
    monkeypatch.setenv("SCHEMA_REGISTRY_URL", registry_url)
    builder = builder_type(
        consumer_config={
            "bootstrap.servers": KAFKA_URL,
            "group.id": group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        },
        neo4j_config={"uri": NEO4J_URL, "user": NEO4J_AUTH[0], "password": NEO4J_AUTH[1]},
    )
    assert builder.allow_json_fallback is False, "JSON fixture fallback must be disabled"
    assert builder.avro_deserializer is not None, "A real Avro deserializer must load"
    builder.BATCH_SIZE = 1
    return builder


def poll_one(topic):
    consumer = Consumer({
        "bootstrap.servers": KAFKA_URL,
        "group.id": "graphguard-wire-inspection-" + uuid.uuid4().hex,
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([topic])
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            msg = consumer.poll(1)
            if msg is None:
                continue
            assert msg.error() is None, str(msg.error())
            return msg
        pytest.fail(f"No message received from {topic}")
    finally:
        consumer.close()


def assert_graph_record(transaction_id, amount):
    driver = GraphDatabase.driver(NEO4J_URL, auth=NEO4J_AUTH)
    try:
        with driver.session() as session:
            rows = session.run(
                """MATCH (u:User)-[:PERFORMED]->(t:Transaction)-[:PAID_TO]->(m:Merchant)
                   MATCH (t)-[:USED_DEVICE]->(d:Device)
                   WHERE t.id = $id
                   RETURN t.amount AS amount, t.payload_sha256 AS digest,
                          u.id AS user_id, m.id AS merchant_id, d.id AS device_id""",
                id=transaction_id,
            ).data()
            assert len(rows) == 1, rows
            row = rows[0]
            assert row["amount"] == amount
            assert len(row["digest"]) == 64
            assert row["user_id"] == "synthetic-avro-user"
            assert row["merchant_id"] == "synthetic-avro-merchant"
            assert row["device_id"] == "synthetic-avro-device"
    finally:
        driver.close()


def assert_ledger(ledger_path, transaction_id, *, expected_conflicts):
    from transaction_ledger import TransactionLedger
    ledger = TransactionLedger(str(ledger_path))
    try:
        rows = ledger.connection.execute(
            "SELECT payload_json, source_topic FROM transactions WHERE transaction_id=?",
            (transaction_id,),
        ).fetchall()
        assert len(rows) == 1, rows
        event = json.loads(rows[0][0])
        assert event["amount"] == 17.25
        assert event["schema_version"] == 1
        assert "ip_address" not in event and "card_last4" not in event
        assert ledger.connection.execute(
            "SELECT COUNT(*) FROM transaction_conflicts WHERE transaction_id=?",
            (transaction_id,),
        ).fetchone()[0] == expected_conflicts
    finally:
        ledger.close()


def test_real_producer_avro_registry_graph_duplicate_conflict_and_replay(tmp_path, monkeypatch):
    create_topics(AvroProducer.TOPIC, AvroBuilder.DLQ_TOPIC)
    transaction_id = "synthetic-registered-avro-001"
    one = make_event(transaction_id)
    publish(AvroProducer, [one, one, make_event(transaction_id, amount=999.0)])
    wire_msg = poll_one(AvroProducer.TOPIC)
    wire = wire_msg.value()
    assert wire[0] == 0, "Must be Confluent Avro framing, never plain JSON"
    assert int.from_bytes(wire[1:5], "big") > 0, "Registry schema ID is required"

    # Verify an actual subject was registered, not just local serialization.
    with urlopen(f"{REGISTRY_URL}/subjects/{AvroProducer.TOPIC}-value/versions", timeout=10) as response:
        versions = json.load(response)
    assert versions and all(isinstance(version, int) for version in versions)

    ledger_path = tmp_path / "registered-avro.sqlite3"
    start_builder(AvroBuilder, "graphguard-avro-initial-" + uuid.uuid4().hex, ledger_path, monkeypatch).run(max_messages=3)
    assert_graph_record(transaction_id, 17.25)
    assert_ledger(ledger_path, transaction_id, expected_conflicts=1)
    dlq_msg = poll_one(AvroBuilder.DLQ_TOPIC)
    assert dict(dlq_msg.headers() or [])["error"] == b"TransactionIdConflict"

    # Fresh group intentionally replays the *same Avro bytes* through actual registry.
    start_builder(AvroBuilder, "graphguard-avro-replay-" + uuid.uuid4().hex, ledger_path, monkeypatch).run(max_messages=3)
    assert_graph_record(transaction_id, 17.25)
    assert_ledger(ledger_path, transaction_id, expected_conflicts=1)


def test_unreachable_registry_does_not_commit_and_recovery_replays(tmp_path, monkeypatch):
    create_topics(OutageProducer.TOPIC, OutageBuilder.DLQ_TOPIC)
    transaction_id = "synthetic-registered-avro-outage"
    publish(OutageProducer, [make_event(transaction_id)])
    group = "graphguard-avro-recover-" + uuid.uuid4().hex
    ledger_path = tmp_path / "registry-recovery.sqlite3"

    # New deserializer with a broken registry endpoint simulates an outage.
    # The broker, bytes and ledger remain real; the original Kafka offset
    # cannot be committed until the schema ID can be decoded.
    failed = start_builder(
        OutageBuilder, group, ledger_path, monkeypatch,
        registry_url="http://127.0.0.1:1",
    )
    with pytest.raises(Exception, match="Avro/Schema Registry decode failed"):
        failed.run(max_messages=1)

    from transaction_ledger import TransactionLedger
    ledger = TransactionLedger(str(ledger_path))
    try:
        assert ledger.connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
    finally:
        ledger.close()

    # Recover with SAME consumer group (not a fresh-offset trick).
    start_builder(OutageBuilder, group, ledger_path, monkeypatch).run(max_messages=1)
    assert_graph_record(transaction_id, 17.25)
    assert_ledger(ledger_path, transaction_id, expected_conflicts=0)
