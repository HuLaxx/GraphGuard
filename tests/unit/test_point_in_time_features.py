"""P1: leakage, windows, late arrivals, duplicates and immutable snapshot proofs.

All inputs are synthetic and all calculations execute against the real local
SQLite ledger. No Neo4j/Kafka service is required for these focused tests.
"""
import json
from pathlib import Path
import sys

import pytest

CONSUMERS = Path(__file__).resolve().parents[2] / "data-eng" / "consumers"
sys.path.insert(0, str(CONSUMERS))
from transaction_ledger import TransactionLedger
from point_in_time_features import FEATURE_VERSION, PointInTimeFeatureStore

HOUR = 3_600_000
DAY = 24 * HOUR
T = 1_790_000_000_000


def event(transaction_id, when, *, user="u1", device="d1",
          merchant="m1", amount=17.25, currency="GBP"):
    return {
        "transaction_id": transaction_id,
        "user_id": user,
        "device_id": device,
        "merchant_id": merchant,
        "amount": amount,
        "currency": currency,
        "timestamp": when,
        "schema_version": 1,
        "idempotency_key": "a" * 64,
    }


def put(ledger, item, offset):
    return ledger.record(item, topic="transactions.raw", partition=0, offset=offset)


def seeded(tmp_path):
    ledger = TransactionLedger(str(tmp_path / "ledger.sqlite3"))
    source = [
        event("h1", T - HOUR, amount=10),
        event("h2", T - 3 * HOUR, user="u2", merchant="m2", amount=20),
        event("h3", T - 25 * HOUR, device="d2", amount=30),
        event("h4", T - 10 * DAY, amount=40),
        event("future", T + HOUR, amount=2000),
        event("same-time", T, amount=800),
        event("cross-currency", T - 2 * HOUR, user="u1", device="d3",
              merchant="m3", amount=1000, currency="USD"),
    ]
    for offset, item in enumerate(source):
        assert put(ledger, item, offset).status == "new"
    assert put(ledger, event("target", T), len(source)).status == "new"
    return ledger


def test_past_only_graph_context_windows_and_currency(tmp_path):
    ledger = seeded(tmp_path)
    store = PointInTimeFeatureStore(ledger.connection)
    snap = store.snapshot_for("target")
    f = snap["features"]
    assert snap["feature_version"] == FEATURE_VERSION
    assert snap["event_time_ms"] == T
    # A future record and earlier-observed same-time record must not leak.
    assert f["user_txn_count_24h"] == 2  # h1 + cross-currency
    assert f["merchant_txn_count_24h"] == 1  # h1 only
    assert f["device_txn_count_7d"] == 2  # h1 + h2
    assert f["device_distinct_users_7d"] == 2
    assert f["device_other_users_7d"] == 1
    assert f["merchant_distinct_users_7d"] == 1  # h1 + h3, same user
    assert f["user_merchant_txn_count_30d"] == 3  # h1 h3 h4
    assert f["user_distinct_devices_30d"] == 3  # d1 d2 d3
    # Never add dollars to pounds.
    assert f["user_same_currency_txn_count_24h"] == 1
    assert f["user_same_currency_amount_sum_24h"] == 10
    assert f["user_same_currency_amount_avg_24h"] == 10
    assert "user_id" not in json.dumps(snap)
    assert "is_fraud" not in json.dumps(snap)
    ledger.close()


def test_late_backfill_cannot_retroactively_change_or_recompute_snapshot(tmp_path):
    ledger = TransactionLedger(str(tmp_path / "late.db"))
    put(ledger, event("early", T - HOUR, amount=10), 1)
    put(ledger, event("target", T), 2)
    store = PointInTimeFeatureStore(ledger.connection)
    first = store.snapshot_for("target")
    assert first["features"]["user_txn_count_24h"] == 1

    # Arrives after target was first observed, despite earlier event-time.
    put(ledger, event("late", T - 2 * HOUR, amount=400), 3)
    assert store.snapshot_for("target") == first
    # Even if an operator rebuilds this fixture, receipt-order gate excludes late.
    ledger.connection.execute(
        "DELETE FROM transaction_feature_snapshots WHERE transaction_id='target'"
    )
    ledger.connection.commit()
    assert store.snapshot_for("target") == first

    put(ledger, event("newer-target", T + HOUR), 4)
    newer = store.snapshot_for("newer-target")["features"]
    assert newer["user_txn_count_24h"] == 3  # early, late, original target
    ledger.close()


def test_replay_duplicate_identity_and_snapshot_hash_are_stable(tmp_path):
    path = tmp_path / "replay.db"
    ledger = TransactionLedger(str(path))
    source = event("target", T)
    assert put(ledger, source, 7).status == "new"
    store = PointInTimeFeatureStore(ledger.connection)
    first = store.snapshot_for("target")
    stored_hash = ledger.connection.execute(
        "SELECT features_sha256 FROM transaction_feature_snapshots"
    ).fetchone()[0]
    ledger.close()
    reopened = TransactionLedger(str(path))
    assert put(reopened, source, 8).status == "duplicate"
    assert PointInTimeFeatureStore(reopened.connection).snapshot_for("target") == first
    assert reopened.connection.execute(
        "SELECT COUNT(*) FROM transaction_feature_snapshots"
    ).fetchone()[0] == 1
    assert reopened.connection.execute(
        "SELECT features_sha256 FROM transaction_feature_snapshots"
    ).fetchone()[0] == stored_hash
    assert put(reopened, event("target", T, amount=600), 9).status == "conflict"
    assert PointInTimeFeatureStore(reopened.connection).snapshot_for("target") == first
    reopened.close()


def test_window_boundaries_and_data_contract_fail_closed(tmp_path):
    ledger = TransactionLedger(str(tmp_path / "boundaries.db"))
    put(ledger, event("at-24h", T - DAY), 1)
    put(ledger, event("before-24h", T - DAY - 1), 2)
    put(ledger, event("target", T), 3)
    features = PointInTimeFeatureStore(ledger.connection).snapshot_for("target")["features"]
    assert features["user_txn_count_24h"] == 1

    # An invalid accepted-record fixture cannot silently enter model features.
    put(ledger, event("bad", T + HOUR, amount=float("nan")), 4)
    with pytest.raises(ValueError):
        PointInTimeFeatureStore(ledger.connection).snapshot_for("bad")
    assert ledger.connection.execute(
        "SELECT COUNT(*) FROM transaction_feature_snapshots WHERE transaction_id='bad'"
    ).fetchone()[0] == 0
    ledger.close()


def test_no_target_labels_ever_used_in_feature_values(tmp_path):
    ledger = TransactionLedger(str(tmp_path / "labels.db"))
    first = event("prior", T - HOUR)
    first["is_fraud"] = True  # synthetic illustration; not a supported input label
    put(ledger, first, 1)
    put(ledger, event("target", T), 2)
    snapshot = PointInTimeFeatureStore(ledger.connection).snapshot_for("target")
    assert snapshot["features"]["user_txn_count_24h"] == 1
    assert "is_fraud" not in json.dumps(snapshot)
    ledger.close()
