"""Model-derived synthetic SHAP proof: exactness, identity, replay and tampering.

No SHAP-looking heuristic feature importance is accepted as evidence.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import pytest
from xgboost import DMatrix

from ml.training.pit_baselines import FEATURE_COLUMNS, run_experiment
from ml.serving.verified_pit_scorer import (
    RESEARCH_STATUS, ScoringContractError,
    VerifiedSyntheticScorer, save_research_score,
)
from ml.explainability.verified_shap import (
    ATTRIBUTION_SCALE, EXPLAINER_VERSION,
    explain_transaction, save_research_explanation,
)

ROOT = Path(__file__).resolve().parents[2]
CONSUMERS = ROOT / "data-eng" / "consumers"
sys.path.insert(0, str(CONSUMERS))
from point_in_time_features import PointInTimeFeatureStore
from transaction_ledger import TransactionLedger

BASE_MS = 1_790_000_000_000


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def trained_root(tmp_path_factory):
    base = tmp_path_factory.mktemp("shap-trained")
    run_experiment(base, count=240, seed=42)
    return base


@pytest.fixture
def accepted(tmp_path, trained_root):
    # A separate ledger from the training fixture. No labels are ever saved
    # into this accepted-source path or its point-in-time feature snapshot.
    artifacts = tmp_path / "models"
    shutil.copytree(trained_root, artifacts)
    ledger = TransactionLedger(str(tmp_path / "accepted.sqlite3"))
    store = PointInTimeFeatureStore(ledger.connection)
    hist = {
        "transaction_id": "synthetic-shap-history",
        "user_id": "synthetic-scorer-user",
        "merchant_id": "synthetic-scorer-merchant",
        "device_id": "synthetic-shared",
        "amount": 20.0,
        "currency": "GBP",
        "timestamp": BASE_MS - 3_600_000,
        "schema_version": 1,
        "idempotency_key": "a" * 64,
    }
    target = dict(
        hist, transaction_id="synthetic-shap-target",
        amount=120.5, timestamp=BASE_MS, idempotency_key="b" * 64,
    )
    for i, record in enumerate((hist, target)):
        assert ledger.record(
            record, topic="synthetic.shap", partition=0, offset=i
        ).status == "new"
        store.snapshot_for(record["transaction_id"])
    try:
        yield artifacts, ledger, target
    finally:
        ledger.close()


def pin_selected(folder: Path, selected: str):
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["selected_by_validation_pr_auc"] = selected
    manifest_path.write_bytes(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    )
    return VerifiedSyntheticScorer(
        folder, expected_manifest_sha256=hash_file(manifest_path),
    )


@pytest.mark.parametrize("model", ["xgboost", "logistic_regression"])
def test_actual_shap_contributions_reconstruct_exact_scored_model(accepted, model):
    folder, ledger, txn = accepted
    scorer = pin_selected(folder, model)
    exp = explain_transaction(ledger.connection, txn["transaction_id"], scorer=scorer)
    score = scorer.score(ledger.connection, txn["transaction_id"])
    assert exp["method"].startswith(
        "xgboost_native_exact_tree_shap" if model == "xgboost"
        else "analytic_linear_shap"
    )
    assert exp["attribution_scale"] == ATTRIBUTION_SCALE
    assert exp["status"] == RESEARCH_STATUS
    assert exp["explainer_version"] == EXPLAINER_VERSION
    assert exp["verified_model_probability"] == score["score"]
    assert exp["model_sha256"] == score["model_sha256"]
    assert exp["source_payload_sha256"] == score["source_payload_sha256"]
    assert exp["feature_snapshot_sha256"] == score["feature_snapshot_sha256"]
    assert exp["manifest_sha256"] == score["manifest_sha256"]
    assert exp["feature_version"] == "pit-v1"
    assert exp["reconstruction_abs_error"] <= 2e-5
    assert len(exp["all_features"]) == len(FEATURE_COLUMNS)
    assert len(exp["top_features"]) == 5
    assert set(i["feature"] for i in exp["all_features"]) == set(FEATURE_COLUMNS)
    assert sum(i["shap_log_odds"] for i in exp["all_features"]) + exp["base_log_odds"] == pytest.approx(
        exp["reconstructed_log_odds"], abs=2e-5,
    )
    ranked = [abs(x["shap_log_odds"]) for x in exp["top_features"]]
    assert ranked == sorted(ranked, reverse=True)
    content = json.dumps(exp)
    for forbidden in ("card_last4", "ip_address", "synthetic_label", "fraud_ring_id"):
        assert forbidden not in content
    assert "not causal" in exp["non_causal_notice"].lower()


def test_native_tree_shap_values_match_underlying_booster_not_heuristics(accepted):
    folder, ledger, txn = accepted
    scorer = pin_selected(folder, "xgboost")
    exp = explain_transaction(ledger.connection, txn["transaction_id"], scorer=scorer, top_k=12)
    source = json.loads(ledger.connection.execute(
        "SELECT payload_json FROM transactions WHERE transaction_id=?",
        (txn["transaction_id"],),
    ).fetchone()[0])
    snapshot = json.loads(ledger.connection.execute(
        "SELECT features_json FROM transaction_feature_snapshots WHERE transaction_id=?",
        (txn["transaction_id"],),
    ).fetchone()[0])
    vector = dict(snapshot["features"], current_amount=source["amount"])
    matrix = np.asarray([[vector[key] for key in FEATURE_COLUMNS]], dtype=np.float64)
    expected = scorer.model.get_booster().predict(
        DMatrix(matrix), pred_contribs=True, approx_contribs=False,
    )[0]
    assert np.allclose(
        [r["shap_log_odds"] for r in exp["all_features"]],
        expected[:-1], rtol=0, atol=1e-9,
    )
    assert exp["base_log_odds"] == pytest.approx(float(expected[-1]), abs=1e-9)
    assert exp["reconstructed_probability"] == pytest.approx(
        scorer.model.predict_proba(matrix)[0, 1], abs=2e-5,
    )


def test_model_outcomes_are_stable_on_replay_and_verified_research_persistence(accepted):
    folder, ledger, txn = accepted
    scorer = pin_selected(folder, "xgboost")
    exp = explain_transaction(ledger.connection, txn["transaction_id"], scorer=scorer)
    score = scorer.score(ledger.connection, txn["transaction_id"])
    with pytest.raises(ScoringContractError, match="Matching verified saved research score"):
        save_research_explanation(ledger.connection, exp, scorer=scorer)
    save_research_score(ledger.connection, score, scorer=scorer)
    assert save_research_explanation(ledger.connection, exp, scorer=scorer) == exp
    assert ledger.record(txn, topic="synthetic.shap", partition=0, offset=9).status == "duplicate"
    again = explain_transaction(ledger.connection, txn["transaction_id"], scorer=scorer)
    assert again == exp
    assert save_research_explanation(ledger.connection, again, scorer=scorer) == exp
    rows = ledger.connection.execute(
        "SELECT explanation_json, explanation_sha256 FROM transaction_research_explanations"
    ).fetchall()
    assert len(rows) == 1
    assert json.loads(rows[0][0]) == exp
    assert hashlib.sha256(rows[0][0].encode("utf-8")).hexdigest() == rows[0][1]


def test_forged_first_explanation_write_is_refused(accepted):
    folder, ledger, txn = accepted
    scorer = pin_selected(folder, "xgboost")
    save_research_score(
        ledger.connection, scorer.score(ledger.connection, txn["transaction_id"]),
        scorer=scorer,
    )
    exp = explain_transaction(ledger.connection, txn["transaction_id"], scorer=scorer)
    forged = dict(exp, base_log_odds=exp["base_log_odds"] + 0.4)
    with pytest.raises(ScoringContractError, match="Unverified or mutated SHAP"):
        save_research_explanation(ledger.connection, forged, scorer=scorer)
    assert ledger.connection.execute(
        """SELECT COUNT(*) FROM sqlite_master
           WHERE type='table' AND name='transaction_research_explanations'"""
    ).fetchone()[0] == 0


def test_forged_feature_attribution_and_hash_are_rejected(accepted):
    folder, ledger, txn = accepted
    scorer = pin_selected(folder, "xgboost")
    good = explain_transaction(ledger.connection, txn["transaction_id"], scorer=scorer)
    forged = json.loads(json.dumps(good))
    forged["top_features"][0]["shap_log_odds"] += 1.0
    forged["explanation_sha256"] = hashlib.sha256(b"fake").hexdigest()
    with pytest.raises(ScoringContractError, match="Unverified or mutated SHAP"):
        save_research_explanation(ledger.connection, forged, scorer=scorer)


def test_shap_fails_closed_on_modified_snapshot_even_if_source_still_present(accepted):
    folder, ledger, txn = accepted
    scorer = pin_selected(folder, "xgboost")
    ledger.connection.execute(
        """UPDATE transaction_feature_snapshots SET features_sha256=?
           WHERE transaction_id=?""",
        ("0" * 64, txn["transaction_id"]),
    )
    ledger.connection.commit()
    with pytest.raises(ScoringContractError, match="Source/snapshot SHA"):
        explain_transaction(ledger.connection, txn["transaction_id"], scorer=scorer)


def test_shap_fails_closed_on_wrong_model_manifest_hash(accepted):
    folder, ledger, txn = accepted
    with pytest.raises(ScoringContractError, match="manifest SHA"):
        VerifiedSyntheticScorer(folder, expected_manifest_sha256="f" * 64)


@pytest.mark.parametrize("top_k", [0, 13, -1, True, "5"])
def test_shap_top_k_validated_before_scoring(accepted, top_k):
    folder, ledger, txn = accepted
    scorer = pin_selected(folder, "xgboost")
    with pytest.raises(ScoringContractError, match="top_k"):
        explain_transaction(
            ledger.connection, txn["transaction_id"], scorer=scorer,
            top_k=top_k,
        )


def test_explanation_is_reproducible_and_carries_no_heuristic_importances(accepted):
    folder, ledger, txn = accepted
    scorer = pin_selected(folder, "logistic_regression")
    one = explain_transaction(ledger.connection, txn["transaction_id"], scorer=scorer)
    two = explain_transaction(ledger.connection, txn["transaction_id"], scorer=scorer)
    assert one == two
    assert one["explanation_sha256"] == hashlib.sha256(
        json.dumps(
            {k: v for k, v in one.items() if k != "explanation_sha256"},
            sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode(),
    ).hexdigest()
    assert "importance" not in json.dumps(one)
