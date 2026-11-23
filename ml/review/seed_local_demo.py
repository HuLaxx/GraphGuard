"""Create a deterministic LOCAL UI fixture, model and private demo credentials.

This fast local dashboard fixture uses the actual first-observed ledger and
TreeSHAP machinery, but DOES NOT send a Kafka/Avro message or touch Neo4j.
The full real-service source-to-case path is tested separately in CI.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

from ml.training.pit_baselines import run_experiment
from ml.review.auth import issue_demo_token
from ml.review.case_store import SyntheticReviewStore
from ml.serving.verified_pit_scorer import VerifiedSyntheticScorer

ROOT = Path(__file__).resolve().parents[2]
CONSUMERS = ROOT / "data-eng" / "consumers"
if str(CONSUMERS) not in sys.path:
    sys.path.insert(0, str(CONSUMERS))
from transaction_ledger import TransactionLedger
from point_in_time_features import PointInTimeFeatureStore

T = 1_790_000_000_000
SAMPLE_TARGETS = ("synthetic-ui-review-001", "synthetic-ui-review-002")


def _private_json(path: Path, payload: dict):
    # O_EXCL prevents accidental replacement of an existing credential file.
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
            file.write("\n")
    except Exception:
        path.unlink(missing_ok=True)
        raise


def prepare_demo(workspace: Path) -> dict:
    workspace = workspace.resolve()
    # Never silently overwrite an existing ledger or signing secrets.
    workspace.mkdir(parents=True, mode=0o700, exist_ok=False)
    try:
        artifacts = workspace / "models"
        manifest = run_experiment(artifacts, count=240, seed=42)
        manifest_hash = hashlib.sha256((artifacts / "manifest.json").read_bytes()).hexdigest()
        ledger_path = workspace / "synthetic_ledger.sqlite3"
        ledger = TransactionLedger(str(ledger_path))
        store = PointInTimeFeatureStore(ledger.connection)
        events = (
            ("synthetic-ui-history", 18.0, T - 3_600_000),
            (SAMPLE_TARGETS[0], 175.0, T),
            (SAMPLE_TARGETS[1], 92.25, T + 3_600_000),
        )
        try:
            for i, (transaction_id, amount, timestamp) in enumerate(events):
                item = {
                    "transaction_id": transaction_id,
                    "user_id": "synthetic-ui-user",
                    "merchant_id": "synthetic-ui-merchant",
                    "device_id": "synthetic-ui-device",
                    "amount": amount, "currency": "GBP", "timestamp": timestamp,
                    "schema_version": 1, "idempotency_key": hashlib.sha256(transaction_id.encode()).hexdigest(),
                }
                assert ledger.record(item, topic="synthetic.ui.fixture", partition=0, offset=i).status == "new"
                store.snapshot_for(transaction_id)

            review_key = secrets.token_urlsafe(48)
            audit_key = secrets.token_urlsafe(48)
            scorer = VerifiedSyntheticScorer(artifacts, expected_manifest_sha256=manifest_hash)
            cases = SyntheticReviewStore(
                ledger.connection, scorer=scorer,
                reviewer_signing_key=review_key.encode(),
                audit_signing_key=audit_key.encode(),
            )
            analyst = issue_demo_token(review_key.encode(), subject="analyst.demo", role="analyst")
            opening = cases.open_case(
                analyst, SAMPLE_TARGETS[0], request_id="seed-local-review-case-001",
            )
            assert opening["status"] == "OPEN"
        finally:
            ledger.close()
        config = {
            "GRAPHGUARD_DEMO_REVIEW_KEY": review_key,
            "GRAPHGUARD_DEMO_AUDIT_KEY": audit_key,
            "GRAPHGUARD_LEDGER_PATH": str(ledger_path),
            "GRAPHGUARD_MODEL_DIR": str(artifacts),
            "GRAPHGUARD_TRUSTED_MANIFEST_SHA256": manifest_hash,
        }
        _private_json(workspace / "private_config.json", config)
        _private_json(workspace / "reviewer_tokens.json", {
            "analyst": analyst,
            "admin": issue_demo_token(review_key.encode(), subject="admin.demo", role="admin"),
            "notice": "Private demo bearer tokens, expire in 600 seconds; keep off public repos and screenshots",
        })
        return {
            "workspace": str(workspace),
            "synthetic_cases": 1,
            "unopened_synthetic_transaction": SAMPLE_TARGETS[1],
            "case_id": opening["case_id"],
            "dataset_type": manifest["scope"],
            "model_manifest_sha256": manifest_hash,
            "private_configuration_file": str(workspace / "private_config.json"),
            "private_tokens_file": str(workspace / "reviewer_tokens.json"),
            "note": "Local ledger fixture bypasses Kafka/Neo4j. Real Kafka-to-case is tested separately in GitHub CI.",
        }
    except Exception:
        # Keep partial artifacts for safe diagnosis; do not auto-delete files
        # or user directories after an interrupted or failed seed.
        raise


def main():
    parser = argparse.ArgumentParser(description="Generate safe local GraphGuard synthetic review fixture")
    parser.add_argument("--workspace", type=Path, default=Path(".local/graphguard-review"))
    args = parser.parse_args()
    result = prepare_demo(args.workspace)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
