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

KAFKA_URL = "127.0.0.1:9092"
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



def test_producer_rejects_naive_or_nonfinite_transaction_fields():
    with pytest.raises(ValueError, match="timezone-aware"):
        TransactionEvent(
            transaction_id="synthetic-naive-clock",
            user_id="synthetic-user",
            merchant_id="synthetic-merchant",
            device_id="synthetic-device",
            amount=10.0,
            currency="GBP",
            timestamp=datetime(2026, 9, 21, 12, 0),  # intentionally missing tzinfo
            ip_address="192.0.2.11",
            card_last4="1234",
        )

    with pytest.raises(ValueError):
        make_event("synthetic-infinite-amount", amount=float("inf"))



class TemporalFeatureProducer(TransactionProducer):
    TOPIC = "transactions.pit.acceptance"


class TemporalFeatureBuilder(GraphBuilder):
    TOPIC = TemporalFeatureProducer.TOPIC
    DLQ_TOPIC = "transactions.pit.acceptance.dlq"


def test_real_avro_ingestion_materializes_past_only_features(tmp_path, monkeypatch):
    """Real producer/registry/broker/graph plus immutable ledger features."""
    from datetime import timedelta
    from transaction_ledger import TransactionLedger

    create_topics(TemporalFeatureProducer.TOPIC, TemporalFeatureBuilder.DLQ_TOPIC)
    baseline = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)

    def at(event_id, hours):
        source = make_event(event_id)
        return source.model_copy(update={"timestamp": baseline + timedelta(hours=hours)})

    # A future *event time* arrives at Kafka before the target event.
    publish(TemporalFeatureProducer, [
        at("synthetic-pit-historical", -1),
        at("synthetic-pit-future", 1),
        at("synthetic-pit-target", 0),
    ])
    ledger_path = tmp_path / "temporal-features.sqlite3"
    group = "graphguard-pit-" + uuid.uuid4().hex
    start_builder(TemporalFeatureBuilder, group, ledger_path, monkeypatch).run(max_messages=3)

    assert_graph_record("synthetic-pit-target", 17.25)
    ledger = TransactionLedger(str(ledger_path))
    try:
        original_row = ledger.connection.execute(
            """SELECT features_json, features_sha256
               FROM transaction_feature_snapshots
               WHERE transaction_id='synthetic-pit-target' AND feature_version='pit-v1'"""
        ).fetchone()
        assert original_row is not None
        snapshot = json.loads(original_row[0])
        assert snapshot["features"]["user_txn_count_24h"] == 1
        assert snapshot["features"]["device_txn_count_7d"] == 1
        assert snapshot["features"]["user_same_currency_amount_sum_24h"] == 17.25
        assert "ip_address" not in original_row[0]
        assert "card_last4" not in original_row[0]
    finally:
        ledger.close()

    # A late-arriving historical event cannot mutate the target's first decision.
    publish(TemporalFeatureProducer, [at("synthetic-pit-late", -0.5)])
    start_builder(TemporalFeatureBuilder, group, ledger_path, monkeypatch).run(max_messages=1)
    ledger = TransactionLedger(str(ledger_path))
    try:
        replayed_row = ledger.connection.execute(
            """SELECT features_json, features_sha256
               FROM transaction_feature_snapshots
               WHERE transaction_id='synthetic-pit-target' AND feature_version='pit-v1'"""
        ).fetchone()
        assert replayed_row == original_row
        assert ledger.connection.execute(
            "SELECT COUNT(*) FROM transaction_feature_snapshots"
        ).fetchone()[0] == 4
    finally:
        ledger.close()



class VerifiedInferenceProducer(TransactionProducer):
    TOPIC = "transactions.pit.verified-score"


class VerifiedInferenceBuilder(GraphBuilder):
    TOPIC = VerifiedInferenceProducer.TOPIC
    DLQ_TOPIC = "transactions.pit.verified-score.dlq"


def test_real_avro_transaction_scores_against_hash_pinned_training_artifact(
    tmp_path, monkeypatch,
):
    """End-to-end *synthetic* Avro -> PIT -> native score -> actual SHAP.

    The model is trained offline on separate synthetic samples, then loaded
    with a pinned manifest SHA. No hosted API, live account, automated
    decision, human case or production deployment is exercised.
    """
    import hashlib
    from transaction_ledger import TransactionLedger
    from ml.training.pit_baselines import run_experiment
    from ml.serving.verified_pit_scorer import (
        RESEARCH_STATUS, VerifiedSyntheticScorer, save_research_score,
    )
    from ml.explainability.verified_shap import (
        explain_transaction, save_research_explanation,
    )
    from ml.review.auth import issue_demo_token
    from ml.review.case_store import SyntheticReviewStore
    import secrets

    create_topics(VerifiedInferenceProducer.TOPIC, VerifiedInferenceBuilder.DLQ_TOPIC)
    model_dir = tmp_path / "approved-model"
    manifest = run_experiment(model_dir, count=240, seed=42)
    manifest_sha = hashlib.sha256((model_dir / "manifest.json").read_bytes()).hexdigest()

    # Real registered Avro bytes -> real Kafka -> real Neo4j + durable ledger
    # and per-transaction point-in-time feature snapshots.
    original = make_event("synthetic-end-to-end-model-score", amount=17.25)
    publish(VerifiedInferenceProducer, [original])
    path = tmp_path / "accepted-source.sqlite3"
    group = "graphguard-native-score-" + uuid.uuid4().hex
    start_builder(VerifiedInferenceBuilder, group, path, monkeypatch).run(max_messages=1)
    assert_graph_record(original.transaction_id, 17.25)

    ledger = TransactionLedger(str(path))
    try:
        scorer = VerifiedSyntheticScorer(
            model_dir, expected_manifest_sha256=manifest_sha,
        )
        result = scorer.score(ledger.connection, original.transaction_id)
        assert result["status"] == RESEARCH_STATUS
        assert result["model_name"] == manifest["selected_by_validation_pr_auc"]
        assert result["model_sha256"] in manifest["artifacts_sha256"].values()
        assert result["feature_version"] == "pit-v1"
        assert 0.0 <= result["score"] <= 1.0
        assert len(result["feature_snapshot_sha256"]) == 64
        save_research_score(ledger.connection, result, scorer=scorer)
        explanation = explain_transaction(
            ledger.connection, original.transaction_id, scorer=scorer,
        )
        assert explanation["verified_model_probability"] == result["score"]
        assert explanation["model_sha256"] == result["model_sha256"]
        assert explanation["feature_snapshot_sha256"] == result["feature_snapshot_sha256"]
        assert explanation["reconstruction_abs_error"] <= 2e-5
        assert len(explanation["all_features"]) == 12
        assert len(explanation["explanation_sha256"]) == 64
        assert "not causal" in explanation["non_causal_notice"].lower()
        save_research_explanation(ledger.connection, explanation, scorer=scorer)

        # Actual analyst and admin identity are authenticated via locally
        # minted, short-lived signed demo tokens, not arbitrary POST actors.
        review_key = secrets.token_urlsafe(48).encode("utf-8")
        audit_key = secrets.token_urlsafe(48).encode("utf-8")
        cases = SyntheticReviewStore(
            ledger.connection, scorer=scorer,
            reviewer_signing_key=review_key, audit_signing_key=audit_key,
        )
        analyst = issue_demo_token(review_key, subject="synthetic.analyst", role="analyst")
        admin = issue_demo_token(review_key, subject="synthetic.admin", role="admin")
        opened = cases.open_case(
            analyst, original.transaction_id,
            request_id="kafka-integration-case-open-001",
        )
        assert opened["status"] == "OPEN"
        assert opened["evidence"]["explanation_sha256"] == explanation["explanation_sha256"]
        escalated = cases.decide(
            analyst, opened["case_id"], action="escalate",
            request_id="kafka-integration-escalate-001", expected_version=0,
        )
        assert escalated["status"] == "ESCALATED"
        reviewed = cases.decide(
            admin, opened["case_id"], action="close_review_complete",
            request_id="kafka-integration-admin-close-001", expected_version=1,
        )
        assert reviewed["status"] == "CLOSED_REVIEW_COMPLETE"
        assert reviewed["version"] == 2
        assert reviewed["events"][-1]["reviewer_role"] == "admin"
    finally:
        ledger.close()

    # Actual Kafka replay under a different consumer group must not change
    # the first accepted source, PIT snapshot, or research score.
    start_builder(
        VerifiedInferenceBuilder,
        "graphguard-native-score-replay-" + uuid.uuid4().hex,
        path, monkeypatch,
    ).run(max_messages=1)
    ledger = TransactionLedger(str(path))
    try:
        again = scorer.score(ledger.connection, original.transaction_id)
        assert again == result
        save_research_score(ledger.connection, again, scorer=scorer)
        repeated_shap = explain_transaction(
            ledger.connection, original.transaction_id, scorer=scorer,
        )
        assert repeated_shap == explanation
        save_research_explanation(
            ledger.connection, repeated_shap, scorer=scorer,
        )
        assert ledger.connection.execute(
            "SELECT COUNT(*) FROM transaction_research_scores"
        ).fetchone()[0] == 1
        assert ledger.connection.execute(
            "SELECT COUNT(*) FROM transaction_research_explanations"
        ).fetchone()[0] == 1
        case_replay = SyntheticReviewStore(
            ledger.connection, scorer=scorer,
            reviewer_signing_key=review_key, audit_signing_key=audit_key,
        )
        assert case_replay.get_case(admin, opened["case_id"]) == reviewed
        assert ledger.connection.execute(
            "SELECT COUNT(*) FROM synthetic_review_events"
        ).fetchone()[0] == 3
    finally:
        ledger.close()



class UnifiedBrokerBrowserProducer(TransactionProducer):
    TOPIC = "transactions.avro.unified-browser"


class UnifiedBrokerBrowserBuilder(GraphBuilder):
    TOPIC = UnifiedBrokerBrowserProducer.TOPIC
    DLQ_TOPIC = "transactions.avro.unified-browser.dlq"


@pytest.mark.skipif(
    os.getenv("GRAPHGUARD_BROKER_CHROMIUM") != "1",
    reason="The real Chromium+Kafka+Neo4j single-runner job is opt-in",
)
def test_uninterrupted_registered_avro_to_real_chromium_case(tmp_path, monkeypatch):
    """One *same* registered Kafka event must reach real Chromium and signed audit.

    This differs from prior separate integration and local seed fixtures.
    Real Kafka/Schema Registry, Neo4j, XGBoost, SHAP, FastAPI, Next and
    headless Chromium all run in this SAME ephemeral GitHub Actions job.
    Still a local synthetic case and NOT production cloud/enterprise IAM.
    """
    import hashlib
    import secrets
    import sqlite3

    from ml.review.auth import issue_demo_token
    from ml.review.case_store import SyntheticReviewStore
    from ml.review.run_local_demo import run_local
    from ml.review.seed_local_demo import _private_json
    from ml.serving.verified_pit_scorer import VerifiedSyntheticScorer
    from ml.training.pit_baselines import run_experiment
    from transaction_ledger import TransactionLedger

    txn_id = "synthetic-broker-to-real-chromium-001"
    workspace = tmp_path / "real-broker-chromium"
    workspace.mkdir(mode=0o700)
    artifacts = workspace / "models"
    manifest = run_experiment(artifacts, count=240, seed=42)
    manifest_pin = hashlib.sha256((artifacts / "manifest.json").read_bytes()).hexdigest()

    create_topics(UnifiedBrokerBrowserProducer.TOPIC, UnifiedBrokerBrowserBuilder.DLQ_TOPIC)
    # No direct-seeded substitute: accept the exact event through Schema
    # Registry and Kafka; the graph builder owns the source and PIT writes.
    original = make_event(txn_id, amount=17.25)
    publish(UnifiedBrokerBrowserProducer, [original])
    wire = poll_one(UnifiedBrokerBrowserProducer.TOPIC).value()
    assert wire[0] == 0  # Confluent Avro framing, never a JSON-only fixture.
    assert int.from_bytes(wire[1:5], "big") > 0
    with urlopen(
        f"{REGISTRY_URL}/subjects/{UnifiedBrokerBrowserProducer.TOPIC}-value/versions",
        timeout=10,
    ) as response:
        assert json.load(response), "Registered Avro schema subject must exist"
    ledger_path = workspace / "synthetic_ledger.sqlite3"
    consumer_group = "graphguard-actual-browser-" + uuid.uuid4().hex
    start_builder(
        UnifiedBrokerBrowserBuilder, consumer_group, ledger_path, monkeypatch
    ).run(max_messages=1)
    assert_graph_record(txn_id, 17.25)

    reviewer_secret = secrets.token_urlsafe(48)
    audit_secret = secrets.token_urlsafe(48)
    scorer = VerifiedSyntheticScorer(
        artifacts, expected_manifest_sha256=manifest_pin,
    )
    ledger = TransactionLedger(str(ledger_path))
    try:
        accepted = ledger.connection.execute(
            "SELECT payload_sha256, source_topic FROM transactions WHERE transaction_id=?",
            (txn_id,),
        ).fetchone()
        assert accepted is not None
        assert accepted[1] == UnifiedBrokerBrowserProducer.TOPIC
        source_sha = accepted[0]
        # Actual Neo4j source hash must equal the accepted SQLite source.
        driver = GraphDatabase.driver(NEO4J_URL, auth=NEO4J_AUTH)
        try:
            with driver.session() as session:
                rows = session.run(
                    "MATCH (t:Transaction {id: $id}) RETURN t.payload_sha256 AS digest",
                    id=txn_id,
                ).data()
            assert len(rows) == 1 and rows[0]["digest"] == source_sha
        finally:
            driver.close()
        opening = SyntheticReviewStore(
            ledger.connection, scorer=scorer,
            reviewer_signing_key=reviewer_secret.encode(),
            audit_signing_key=audit_secret.encode(),
        ).open_case(
            issue_demo_token(
                reviewer_secret.encode(), subject="analyst.demo", role="analyst"
            ),
            txn_id, request_id="unified-kafka-chromium-open-001",
        )
        assert opening["status"] == "OPEN"
        assert opening["evidence"]["source_payload_sha256"] == source_sha
        assert opening["evidence"]["manifest_sha256"] == manifest_pin
        assert len(opening["events"]) == 1
    finally:
        ledger.close()

    _private_json(workspace / "private_config.json", {
        "GRAPHGUARD_DEMO_REVIEW_KEY": reviewer_secret,
        "GRAPHGUARD_DEMO_AUDIT_KEY": audit_secret,
        "GRAPHGUARD_LEDGER_PATH": str(ledger_path),
        "GRAPHGUARD_MODEL_DIR": str(artifacts),
        "GRAPHGUARD_TRUSTED_MANIFEST_SHA256": manifest_pin,
    })
    # The runner generates its own short-lived private reviewer_tokens.json.
    evidence_dir = Path(
        os.environ.get(
            "GRAPHGUARD_BROKER_CHROMIUM_EVIDENCE_DIR",
            str(tmp_path / "verified-source-to-browser-evidence"),
        )
    )
    run_local(
        workspace, browser_smoke=True, evidence_dir=evidence_dir,
        expected_transaction_id=txn_id,
        source_mode="real_kafka_avro_neo4j",
    )
    report_path = evidence_dir / "synthetic-review-proof.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["source_mode"] == "real_kafka_avro_neo4j"
    assert report["transaction_id"] == txn_id
    assert report["source_sha256"] == source_sha
    assert report["model_sha256"] == opening["evidence"]["model_sha256"]
    assert report["shap_sha256"] == opening["evidence"]["explanation_sha256"]
    assert report["final_status"] == "CLOSED_REVIEW_COMPLETE"
    assert report["final_version"] == 2
    assert report["steps_passed"] == 6
    assert report["external_provider_calls"] == 0
    assert (evidence_dir / "synthetic-review-final.png").is_file()

    # Read the SAME broker-produced source after real Chromium reviewer
    # actions. The source, first PIT snapshot and case anchor remain stable.
    with sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE transaction_id=?", (txn_id,)
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM transaction_research_scores WHERE transaction_id=?",
            (txn_id,),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM transaction_research_explanations WHERE transaction_id=?",
            (txn_id,),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM synthetic_review_cases WHERE transaction_id=?",
            (txn_id,),
        ).fetchone()[0] == 1
        assert conn.execute(
            "SELECT COUNT(*) FROM synthetic_review_events WHERE case_id=?",
            (opening["case_id"],),
        ).fetchone()[0] == 3
        snapshot = conn.execute(
            "SELECT features_sha256 FROM transaction_feature_snapshots WHERE transaction_id=?",
            (txn_id,),
        ).fetchone()
        assert snapshot is not None
        assert snapshot[0] == opening["evidence"]["feature_snapshot_sha256"]
    assert_graph_record(txn_id, 17.25)
    # An explicit Kafka replay in the SAME job must keep all case records.
    start_builder(
        UnifiedBrokerBrowserBuilder,
        "graphguard-actual-browser-replay-" + uuid.uuid4().hex,
        ledger_path, monkeypatch,
    ).run(max_messages=1)
    with sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM synthetic_review_events WHERE case_id=?",
            (opening["case_id"],),
        ).fetchone()[0] == 3
    assert_graph_record(txn_id, 17.25)
    print("PASS: SAME registered Kafka event → Neo4j → PIT → ML/SHAP → signed real Chromium reviewer and replay")
