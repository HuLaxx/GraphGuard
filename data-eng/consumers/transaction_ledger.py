"""Local, durable source ledger for synthetic transaction ingestion.

SQLite is deliberately a development boundary, not a distributed exactly-once
guarantee. Commit its source record before updating the derived Neo4j graph.
A crash after the ledger write is repaired by replaying Kafka.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class RecordResult:
    status: str  # new | duplicate | conflict
    payload_hash: str


def canonical_payload(transaction: dict) -> str:
    # Data minimization: raw IP address and card fragments are not retained
    # in this local normalized ledger or included in graph identity.
    # This ledger is restricted to synthetic development inputs.
    excluded = {"payload_sha256", "ip_address", "card_last4"}
    source = {k: v for k, v in transaction.items() if k not in excluded}
    # Writer-schema defaults and a double amount have the same identity
    # whether supplied explicitly or resolved by a compatible reader.
    source.setdefault("schema_version", 1)
    if isinstance(source.get("amount"), (int, float)) and not isinstance(source["amount"], bool):
        source["amount"] = float(source["amount"])
    return json.dumps(source, sort_keys=True, separators=(",", ":"), allow_nan=False)


class TransactionLedger:
    """Persistent, unique-ID source records with an auditable conflict inbox."""

    def __init__(self, path: str):
        if path != ":memory:":
            Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=30)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id TEXT PRIMARY KEY,
                payload_sha256 TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                source_topic TEXT NOT NULL,
                source_partition INTEGER NOT NULL,
                source_offset INTEGER NOT NULL,
                received_at_utc TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS transaction_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL,
                original_sha256 TEXT NOT NULL,
                incoming_sha256 TEXT NOT NULL,
                incoming_payload_json TEXT NOT NULL,
                source_topic TEXT NOT NULL,
                source_partition INTEGER NOT NULL,
                source_offset INTEGER NOT NULL,
                received_at_utc TEXT NOT NULL,
                UNIQUE(source_topic, source_partition, source_offset)
            );
            """
        )

    def record(self, transaction: dict, *, topic: str, partition: int, offset: int) -> RecordResult:
        raw = canonical_payload(transaction)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        transaction_id = transaction["transaction_id"]
        received_at = datetime.now(timezone.utc).isoformat()

        # Serialize competing writers around the identity lookup + insert.
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            original = self.connection.execute(
                "SELECT payload_sha256 FROM transactions WHERE transaction_id = ?",
                (transaction_id,),
            ).fetchone()
            if original is None:
                self.connection.execute(
                    """INSERT INTO transactions
                       (transaction_id, payload_sha256, payload_json, source_topic,
                        source_partition, source_offset, received_at_utc)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (transaction_id, digest, raw, topic, partition, offset, received_at),
                )
                status = "new"
            elif original[0] == digest:
                status = "duplicate"
            else:
                self.connection.execute(
                    """INSERT OR IGNORE INTO transaction_conflicts
                       (transaction_id, original_sha256, incoming_sha256,
                        incoming_payload_json, source_topic, source_partition,
                        source_offset, received_at_utc)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (transaction_id, original[0], digest, raw, topic, partition, offset, received_at),
                )
                status = "conflict"
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
        return RecordResult(status=status, payload_hash=digest)

    def close(self) -> None:
        self.connection.close()
