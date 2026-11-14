"""Leakage-safe, local point-in-time graph-context features for synthetic events.

Uses the *first accepted* SQLite transaction ledger record, not the mutable
current Neo4j state. Both event time and source observation order are gated:
a late-arriving event cannot rewrite an earlier decision snapshot.

This is a reproducible demo feature builder; no real-customer / production claim.
"""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from math import isfinite
import sqlite3

FEATURE_VERSION = "pit-v1"
HOUR_MS = 60 * 60 * 1000
DAY_MS = 24 * HOUR_MS


def _event(raw: str) -> dict:
    event = json.loads(raw)
    timestamp = event.get("timestamp")
    amount = event.get("amount")
    if type(timestamp) is not int or timestamp <= 0:
        raise ValueError("Event time must be positive UTC epoch milliseconds")
    if type(amount) not in (float, int) or not isfinite(amount) or amount <= 0:
        raise ValueError("Amount must be positive and finite")
    for name in ("transaction_id", "user_id", "device_id", "merchant_id", "currency"):
        if not isinstance(event.get(name), str) or not event[name].strip():
            raise ValueError(f"Required normalized field missing: {name}")
    return event


def _within(event_time: int, cutoff: int, duration_ms: int) -> bool:
    # Strictly earlier event time, lower bound inclusive. Same-timestamp events
    # cannot observe one another regardless of their Kafka/SQLite receipt order.
    return cutoff - duration_ms <= event_time < cutoff


def derive_graph_context(target: dict, history: list[dict]) -> dict:
    """Deterministic features from accepted, earlier-known normalized transactions.

    Callers MUST filter history by first-observed ledger rowid/received timestamp;
    this pure function additionally enforces strict event-time exclusions.
    """
    t = target["timestamp"]
    user = target["user_id"]
    device = target["device_id"]
    merchant = target["merchant_id"]
    currency = target["currency"]
    user_24h = []
    merchant_24h = []
    device_7d = []
    merchant_7d = []
    user_merchant_30d = []
    user_30d = []
    for event in history:
        when = event["timestamp"]
        if when >= t:
            continue
        if event["user_id"] == user and _within(when, t, DAY_MS):
            user_24h.append(event)
        if event["merchant_id"] == merchant and _within(when, t, DAY_MS):
            merchant_24h.append(event)
        if event["device_id"] == device and _within(when, t, 7 * DAY_MS):
            device_7d.append(event)
        if event["merchant_id"] == merchant and _within(when, t, 7 * DAY_MS):
            merchant_7d.append(event)
        if event["user_id"] == user and _within(when, t, 30 * DAY_MS):
            user_30d.append(event)
            if event["merchant_id"] == merchant:
                user_merchant_30d.append(event)

    # Monetary aggregates are same-currency only (no invented FX conversions).
    same_currency = [e for e in user_24h if e["currency"] == currency]
    amount_total = sum((Decimal(str(e["amount"])) for e in same_currency), Decimal("0"))
    amount_avg = (
        amount_total / len(same_currency) if same_currency else Decimal("0")
    )
    return {
        "user_txn_count_24h": len(user_24h),
        "user_same_currency_txn_count_24h": len(same_currency),
        "user_same_currency_amount_sum_24h": round(float(amount_total), 2),
        "user_same_currency_amount_avg_24h": round(float(amount_avg), 2),
        "merchant_txn_count_24h": len(merchant_24h),
        "device_txn_count_7d": len(device_7d),
        "device_distinct_users_7d": len({e["user_id"] for e in device_7d}),
        "device_other_users_7d": len({e["user_id"] for e in device_7d if e["user_id"] != user}),
        "merchant_distinct_users_7d": len({e["user_id"] for e in merchant_7d}),
        "user_merchant_txn_count_30d": len(user_merchant_30d),
        "user_distinct_devices_30d": len({e["device_id"] for e in user_30d}),
    }


class PointInTimeFeatureStore:
    """Immutable, versioned per-transaction snapshots in the existing ledger DB."""

    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS transaction_feature_snapshots (
                transaction_id TEXT NOT NULL,
                feature_version TEXT NOT NULL,
                source_payload_sha256 TEXT NOT NULL,
                observation_cutoff_rowid INTEGER NOT NULL,
                observation_cutoff_utc TEXT NOT NULL,
                event_time_ms INTEGER NOT NULL,
                features_json TEXT NOT NULL,
                features_sha256 TEXT NOT NULL,
                computed_at_utc TEXT NOT NULL,
                PRIMARY KEY(transaction_id, feature_version)
            )
            """
        )

    def snapshot_for(self, transaction_id: str) -> dict:
        """Return the first persisted result, never retrospectively refit it.

        Snapshot calculations fail before offset acknowledgment on bad ledger
        records. A restart/replay reads the same immutable result.
        """
        existing = self.connection.execute(
            """SELECT features_json FROM transaction_feature_snapshots
               WHERE transaction_id = ? AND feature_version = ?""",
            (transaction_id, FEATURE_VERSION),
        ).fetchone()
        if existing:
            return json.loads(existing[0])

        target_row = self.connection.execute(
            """SELECT rowid, payload_json, payload_sha256, received_at_utc
               FROM transactions WHERE transaction_id = ?""",
            (transaction_id,),
        ).fetchone()
        if target_row is None:
            raise KeyError(f"No accepted transaction: {transaction_id}")

        receipt_seq, target_raw, source_hash, observed_at = target_row
        target = _event(target_raw)
        history = [
            _event(row[0])
            for row in self.connection.execute(
                """SELECT payload_json FROM transactions
                   WHERE rowid < ? AND received_at_utc <= ?
                   ORDER BY rowid""",
                (receipt_seq, observed_at),
            )
        ]
        features = derive_graph_context(target, history)
        # This includes only aggregates, dates and hashes, not raw identifiers.
        snapshot = {
            "feature_version": FEATURE_VERSION,
            "event_time_ms": target["timestamp"],
            "as_of_ledger_rowid": receipt_seq,
            "as_of_received_at_utc": observed_at,
            "features": features,
        }
        encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        self.connection.execute(
            """INSERT OR IGNORE INTO transaction_feature_snapshots
               (transaction_id, feature_version, source_payload_sha256,
                observation_cutoff_rowid, observation_cutoff_utc, event_time_ms,
                features_json, features_sha256, computed_at_utc)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                transaction_id, FEATURE_VERSION, source_hash,
                receipt_seq, observed_at, target["timestamp"],
                encoded, digest, datetime.now(timezone.utc).isoformat(),
            ),
        )
        self.connection.commit()
        # Another process may have committed first; return the authoritative
        # first snapshot rather than a computed-but-not-persisted alternative.
        return json.loads(
            self.connection.execute(
                """SELECT features_json FROM transaction_feature_snapshots
                   WHERE transaction_id = ? AND feature_version = ?""",
                (transaction_id, FEATURE_VERSION),
            ).fetchone()[0]
        )
