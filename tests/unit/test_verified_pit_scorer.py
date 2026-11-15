"""Verified pit-v1 research scorer: real training artifacts and local ledger.

This suite is CPU-only and uses deterministic synthetic models/identities.
There are no production decisions, external customers or cloud resources.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from ml.training.pit_baselines import (
    FEATURE_COLUMNS, chronological_split, make_synthetic_dataset, run_experiment,
)
from ml.serving.verified_pit_scorer import (
    RESEARCH_STATUS, ScoringContractError,
    VerifiedSyntheticScorer, save_research_score,
)
import sys

CONSUMERS = Path(__file__).resolve().parents[2] / "data-eng" / "consumers"
sys.path.insert(0, str(CONSUMERS))
from point_in_time_features import PointInTimeFeatureStore
from transaction_ledger import TransactionLedger


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def trained_and_ingested(tmp_path):
    artifacts = tmp_path / "approved"
    manifest = run_experiment(artifacts, count=240, seed=42)
    digest = sha(artifacts / "manifest.json")
    ledger = TransactionLedger(str(tmp_path / "accepted-ledger.sqlite3"))
    ev = {
        "transaction_id": "synthetic-offline-scoring-001",
        "user_id": "synthetic-user",
        "merchant_id": "synthetic-merchant",
        "device_id": "synthetic-device",
        "amount": 56.25,
        "currency": "GBP",
        "timestamp": 1_790_000_000_000,
        "schema_version": 1,
        "idempotency_key": "a" * 64,
    }
    assert ledger.record(ev, topic="synthetic.avro", partition=0, offset=0).status == "new"
    PointInTimeFeatureStore(ledger.connection).snapshot_for(ev["transaction_id"])
    yield artifacts, digest, manifest, ledger, ev
    ledger.close()


def test_verified_model_scores_real_source_snapshot_and_replay(trained_and_ingested):
    folder, digest, manifest, ledger, event = trained_and_ingested
    scorer = VerifiedSyntheticScorer(folder, expected_manifest_sha256=digest)
    result = scorer.score(ledger.connection, event["transaction_id"])
    assert 0.0 <= result["score"] <= 1.0
    assert result["status"] == RESEARCH_STATUS
    assert result["model_name"] == manifest["selected_by_validation_pr_auc"]
    assert result["feature_version"] == manifest["feature_version"]
    assert result["model_sha256"] == manifest["artifacts_sha256"][
        "xgboost_baseline.json" if result["model_name"] == "xgboost" else "logistic_baseline.json"
    ]
    assert len(result["feature_snapshot_sha256"]) == 64

    saved = save_research_score(ledger.connection, result)
    assert saved == result
    assert ledger.record(event, topic="synthetic.avro", partition=0, offset=1).status == "duplicate"
    assert scorer.score(ledger.connection, event["transaction_id"]) == result
    assert save_research_score(ledger.connection, result) == result
    assert ledger.connection.execute("SELECT COUNT(*) FROM transaction_research_scores").fetchone()[0] == 1
    assert ledger.connection.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1


def test_inference_prediction_matches_selected_saved_native_model(trained_and_ingested):
    folder, digest, manifest, ledger, event = trained_and_ingested
    scorer = VerifiedSyntheticScorer(folder, expected_manifest_sha256=digest)
    result = scorer.score(ledger.connection, event["transaction_id"])
    snapshot = json.loads(ledger.connection.execute(
        "SELECT features_json FROM transaction_feature_snapshots WHERE transaction_id=?",
        (event["transaction_id"],),
    ).fetchone()[0])
    features = dict(snapshot["features"])
    features["current_amount"] = event["amount"]
    vector = np.array([[features[k] for k in FEATURE_COLUMNS]], dtype=np.float64)
    if scorer.model_name == "xgboost":
        expected = scorer.model.predict_proba(vector)[0, 1]
        assert result["score"] == pytest.approx(float(expected), abs=1e-8)
    else:
        p = scorer.logistic
        z = np.dot((vector[0] - p["scaler_mean"]) / p["scaler_scale"], p["coefficients"]) + p["intercept"][0]
        expected = 1.0 / (1.0 + np.exp(-z))
        assert result["score"] == pytest.approx(float(expected), abs=1e-8)


def test_missing_pin_and_modified_manifest_or_model_are_rejected(trained_and_ingested):
    folder, digest, manifest, _, _ = trained_and_ingested
    with pytest.raises(ScoringContractError, match="SHA-256 pin"):
        VerifiedSyntheticScorer(folder, expected_manifest_sha256="")
    with pytest.raises(ScoringContractError, match="manifest SHA"):
        VerifiedSyntheticScorer(folder, expected_manifest_sha256="0" * 64)
    name = ("xgboost_baseline.json" if manifest["selected_by_validation_pr_auc"] == "xgboost"
            else "logistic_baseline.json")
    artifact = folder / name
    original = artifact.read_bytes()
    artifact.write_bytes(original + b"tampered")
    with pytest.raises(ScoringContractError, match="artifact SHA"):
        VerifiedSyntheticScorer(folder, expected_manifest_sha256=digest)
    artifact.write_bytes(original)
    manifest_file = folder / "manifest.json"
    original_manifest = manifest_file.read_bytes()
    manifest_file.write_bytes(original_manifest + b" ")
    with pytest.raises(ScoringContractError, match="manifest SHA"):
        VerifiedSyntheticScorer(folder, expected_manifest_sha256=digest)


def test_missing_features_or_mutated_ledger_blocks_scoring(trained_and_ingested):
    folder, digest, _, ledger, event = trained_and_ingested
    scorer = VerifiedSyntheticScorer(folder, expected_manifest_sha256=digest)
    with pytest.raises(ScoringContractError, match="Unaccepted transaction"):
        scorer.score(ledger.connection, "not-yet-ingested")
    ledger.connection.execute(
        "UPDATE transaction_feature_snapshots SET features_sha256=?",
        ("f" * 64,),
    )
    ledger.connection.commit()
    with pytest.raises(ScoringContractError, match="Source/snapshot SHA"):
        scorer.score(ledger.connection, event["transaction_id"])


def test_source_and_pit_cutoff_drift_fail_closed(trained_and_ingested):
    folder, digest, _, ledger, event = trained_and_ingested
    scorer = VerifiedSyntheticScorer(folder, expected_manifest_sha256=digest)
    ledger.connection.execute(
        "UPDATE transaction_feature_snapshots SET observation_cutoff_rowid=999"
    )
    ledger.connection.commit()
    with pytest.raises(ScoringContractError, match="point-in-time provenance"):
        scorer.score(ledger.connection, event["transaction_id"])


def test_unknown_currency_is_not_silently_converted(trained_and_ingested):
    folder, digest, _, ledger, event = trained_and_ingested
    scorer = VerifiedSyntheticScorer(folder, expected_manifest_sha256=digest)
    source = json.loads(ledger.connection.execute(
        "SELECT payload_json FROM transactions WHERE transaction_id=?",
        (event["transaction_id"],),
    ).fetchone()[0])
    source["currency"] = "USD"
    modified = json.dumps(source, sort_keys=True, separators=(",", ":"))
    ledger.connection.execute(
        "UPDATE transactions SET payload_json=?, payload_sha256=? WHERE transaction_id=?",
        (modified, hashlib.sha256(modified.encode()).hexdigest(), event["transaction_id"]),
    )
    ledger.connection.commit()
    with pytest.raises(ScoringContractError, match="GBP fixtures only"):
        scorer.score(ledger.connection, event["transaction_id"])


def test_untrusted_prediction_cannot_overwrite_first_record(trained_and_ingested):
    folder, digest, _, ledger, event = trained_and_ingested
    scorer = VerifiedSyntheticScorer(folder, expected_manifest_sha256=digest)
    result = scorer.score(ledger.connection, event["transaction_id"])
    save_research_score(ledger.connection, result)
    tampered = dict(result, score=0.0 if result["score"] > 0 else 1.0)
    with pytest.raises(ScoringContractError, match="overwrite prior"):
        save_research_score(ledger.connection, tampered)
    assert ledger.connection.execute("SELECT COUNT(*) FROM transaction_research_scores").fetchone()[0] == 1
