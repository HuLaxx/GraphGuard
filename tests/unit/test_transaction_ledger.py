"""Durable source identity acceptance tests; no external services needed."""
import importlib.util
from pathlib import Path
import sqlite3

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "data-eng/consumers/transaction_ledger.py"
spec = importlib.util.spec_from_file_location("graphguard_transaction_ledger", SOURCE)
module = importlib.util.module_from_spec(spec)
# dataclasses needs its module registered when dynamically imported.
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)
TransactionLedger = module.TransactionLedger


def transaction(amount=17.25):
    return {
        "transaction_id": "synthetic-txn-001",
        "user_id": "synthetic-user",
        "merchant_id": "synthetic-merchant",
        "device_id": "synthetic-device",
        "amount": amount,
        "currency": "GBP",
        "timestamp": 1790000000000,
        "idempotency_key": "a" * 64,
    }


def test_first_write_duplicate_and_conflict_are_durable(tmp_path):
    path = tmp_path / "ledger.sqlite3"
    first = transaction()
    ledger = TransactionLedger(str(path))
    created = ledger.record(first, topic="transactions.raw", partition=0, offset=3)
    assert created.status == "new"
    assert len(created.payload_hash) == 64
    assert ledger.record(dict(reversed(list(first.items()))), topic="transactions.raw", partition=0, offset=4).status == "duplicate"
    assert ledger.record(transaction(500.0), topic="transactions.raw", partition=0, offset=5).status == "conflict"
    assert ledger.record(transaction(500.0), topic="transactions.raw", partition=0, offset=5).status == "conflict"
    ledger.close()

    reopened = TransactionLedger(str(path))
    assert reopened.record(first, topic="transactions.raw", partition=0, offset=6).status == "duplicate"
    row = reopened.connection.execute(
        "SELECT payload_json, source_offset FROM transactions WHERE transaction_id=?",
        (first["transaction_id"],),
    ).fetchone()
    assert row[1] == 3
    assert '"amount":17.25' in row[0]
    conflict = reopened.connection.execute(
        "SELECT COUNT(*), MIN(source_offset) FROM transaction_conflicts"
    ).fetchone()
    assert conflict == (1, 5)
    reopened.close()


def test_different_entity_same_transaction_id_is_conflict(tmp_path):
    ledger = TransactionLedger(str(tmp_path / "identity.db"))
    first = transaction()
    assert ledger.record(first, topic="transactions.raw", partition=1, offset=1).status == "new"
    modified = dict(first, merchant_id="another-synthetic-merchant")
    assert ledger.record(modified, topic="transactions.raw", partition=1, offset=2).status == "conflict"
    ledger.close()


def test_non_finite_payload_rejected_before_persist(tmp_path):
    ledger = TransactionLedger(str(tmp_path / "identity.db"))
    with pytest.raises(ValueError):
        ledger.record(transaction(float("nan")), topic="transactions.raw", partition=0, offset=3)
    assert ledger.connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0
    ledger.close()
