"""Model-derived, additive SHAP explanations for SYNTHETIC GraphGuard scores.

- XGBoost: exact native TreeSHAP via Booster.predict(pred_contribs=True),
  evaluated in raw log-odds (margin) units; no heuristic importance weights.
- Standardized logistic regression: analytic additive Shapley decomposition
  using the frozen train-sample feature mean as the independent baseline.

Explanations are research-only. Feature attribution is NOT causal evidence,
an accusation of real fraud, a calibrated probability or an analyst decision.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import sqlite3

import numpy as np
from xgboost import DMatrix

from ml.serving.verified_pit_scorer import (
    RESEARCH_STATUS, ScoringContractError, VerifiedSyntheticScorer,
)
from ml.training.pit_baselines import FEATURE_COLUMNS

EXPLAINER_VERSION = "pit-shap-v1"
ATTRIBUTION_SCALE = "raw_log_odds"
NO_CAUSAL_CLAIM = "Associations in a synthetic model; not causal evidence or proof of fraud."


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sigmoid(margin: float) -> float:
    return (
        1.0 / (1.0 + math.exp(-margin))
        if margin >= 0
        else math.exp(margin) / (1.0 + math.exp(margin))
    )


def _verified_input(connection: sqlite3.Connection, transaction_id: str,
                    scorer: VerifiedSyntheticScorer):
    """Take source and features from the exact authenticated score snapshot."""
    if not isinstance(scorer, VerifiedSyntheticScorer):
        raise ScoringContractError("Hash-pinned verified scorer is required")
    result = scorer.score(connection, transaction_id)
    source = connection.execute(
        "SELECT payload_json FROM transactions WHERE transaction_id=?",
        (transaction_id,),
    ).fetchone()
    snapshot = connection.execute(
        """SELECT features_json FROM transaction_feature_snapshots
           WHERE transaction_id=? AND feature_version=?""",
        (transaction_id, scorer.feature_version),
    ).fetchone()
    if not source or not snapshot:
        raise ScoringContractError("Accepted source and feature snapshot required")
    if _digest(source[0]) != result["source_payload_sha256"]:
        raise ScoringContractError("Source changed after verified scoring")
    if _digest(snapshot[0]) != result["feature_snapshot_sha256"]:
        raise ScoringContractError("Feature snapshot changed after verified scoring")
    source_event = json.loads(source[0])
    normalized = json.loads(snapshot[0])
    features = normalized.get("features")
    if not isinstance(features, dict) or set(features) != set(FEATURE_COLUMNS) - {"current_amount"}:
        raise ScoringContractError("Source features violate trained feature contract")
    feature_values = {**features, "current_amount": source_event.get("amount")}
    if set(feature_values) != set(FEATURE_COLUMNS):
        raise ScoringContractError("Unexpected model input")
    if not all(type(value) in (int, float) and math.isfinite(value)
               for value in feature_values.values()):
        raise ScoringContractError("Non-finite/non-numeric model feature")
    x = np.asarray([[feature_values[column] for column in FEATURE_COLUMNS]], dtype=np.float64)
    if not np.isfinite(x).all():
        raise ScoringContractError("Non-finite numeric model input")
    return result, x, feature_values


def explain_transaction(connection: sqlite3.Connection, transaction_id: str,
                        *, scorer: VerifiedSyntheticScorer, top_k: int = 5) -> dict:
    """Explain the *same* already verified, synthetic-only model prediction.

    Native TreeSHAP is evaluated directly from the trusted XGBoost booster.
    A separate prediction-reconstruction check prevents decorative SHAP.
    """
    if type(top_k) is not int or not 1 <= top_k <= len(FEATURE_COLUMNS):
        raise ScoringContractError("top_k outside valid feature range")
    score, matrix, feature_values = _verified_input(connection, transaction_id, scorer)
    if score["status"] != RESEARCH_STATUS:
        raise ScoringContractError("Cannot explain a non-research decision")

    if scorer.model_name == "xgboost":
        booster = scorer.model.get_booster()
        dmatrix = DMatrix(matrix)
        # Native XGBoost TreeSHAP; approx_contribs=False is exact tree SHAP
        # in the native tree-path-dependent formulation (no external background).
        native = np.asarray(
            booster.predict(dmatrix, pred_contribs=True, approx_contribs=False),
            dtype=np.float64,
        )
        if native.shape != (1, len(FEATURE_COLUMNS) + 1):
            raise ScoringContractError("Unexpected native TreeSHAP output shape")
        phi, base = native[0, :-1], float(native[0, -1])
        predicted_margin = float(booster.predict(dmatrix, output_margin=True)[0])
        if not math.isclose(float(base + sum(phi)), predicted_margin,
                            rel_tol=1e-6, abs_tol=2e-5):
            raise ScoringContractError("SHAP contributions fail native margin check")
        method = "xgboost_native_exact_tree_shap_path_dependent"
        background = "tree_path_dependent_native_booster"
    elif scorer.model_name == "logistic_regression":
        params = scorer.logistic
        means = np.asarray(params["scaler_mean"], dtype=np.float64)
        scales = np.asarray(params["scaler_scale"], dtype=np.float64)
        weights = np.asarray(params["coefficients"], dtype=np.float64)
        intercept = np.asarray(params["intercept"], dtype=np.float64)
        if (
            means.shape != (len(FEATURE_COLUMNS),)
            or scales.shape != means.shape
            or weights.shape != means.shape
            or intercept.shape != (1,)
            or not np.isfinite(means).all()
            or not np.isfinite(scales).all()
            or not np.isfinite(weights).all()
            or not np.isfinite(intercept).all()
            or np.any(scales <= 0)
        ):
            raise ScoringContractError("Invalid logistic Shapley baseline")
        # Exactly additive Shapley values of a linear logit function,
        # relative to the frozen TRAIN-sample feature expectation.
        phi = weights * (matrix[0] - means) / scales
        base = float(intercept[0])
        predicted_margin = float(base + np.sum(phi))
        method = "analytic_linear_shap_train_mean_baseline"
        background = "frozen_training_feature_means"
    else:
        raise ScoringContractError("Unknown trained explanation method")

    if not np.isfinite(phi).all() or not math.isfinite(base):
        raise ScoringContractError("Non-finite attribution or baseline")
    reconstructed_margin = float(base + np.sum(phi))
    reconstructed_probability = _sigmoid(reconstructed_margin)
    # Both logit-based methods must numerically rebuild the verified
    # predicted probability of this exact selected model and feature vector.
    if not math.isclose(reconstructed_probability, score["score"],
                        rel_tol=1e-5, abs_tol=2e-5):
        raise ScoringContractError("Attributions fail scored-probability reconstruction")

    all_features = [
        {
            "feature": column,
            "value": float(feature_values[column]),
            "shap_log_odds": float(phi[index]),
            "direction": (
                "raises_model_log_odds" if phi[index] > 0
                else "lowers_model_log_odds" if phi[index] < 0
                else "no_log_odds_effect"
            ),
        }
        for index, column in enumerate(FEATURE_COLUMNS)
    ]
    ranked = sorted(all_features, key=lambda item: (-abs(item["shap_log_odds"]), item["feature"]))

    explanation = {
        "transaction_id": transaction_id,
        "scope": "SYNTHETIC_ONLY_RESEARCH_EXPLANATION",
        "status": RESEARCH_STATUS,
        "non_causal_notice": NO_CAUSAL_CLAIM,
        "explainer_version": EXPLAINER_VERSION,
        "method": method,
        "background": background,
        "attribution_scale": ATTRIBUTION_SCALE,
        "base_log_odds": base,
        "reconstructed_log_odds": reconstructed_margin,
        "base_probability": _sigmoid(base),
        "reconstructed_probability": reconstructed_probability,
        "verified_model_probability": float(score["score"]),
        "reconstruction_abs_error": abs(reconstructed_probability - score["score"]),
        "all_features": all_features,
        "top_features": ranked[:top_k],
        "model_name": score["model_name"],
        "model_input_version": score["model_input_version"],
        "model_sha256": score["model_sha256"],
        "manifest_sha256": score["manifest_sha256"],
        "source_payload_sha256": score["source_payload_sha256"],
        "feature_snapshot_sha256": score["feature_snapshot_sha256"],
        "feature_version": score["feature_version"],
        "event_time_ms": score["event_time_ms"],
    }
    explanation["explanation_sha256"] = _digest(_canonical(explanation))
    return explanation


def save_research_explanation(
    connection: sqlite3.Connection, explanation: dict, *,
    scorer: VerifiedSyntheticScorer,
) -> dict:
    """Append the verified explanation after a matching saved research score.

    Writer re-explains with the pinned scorer; caller cannot insert fake SHAP
    values even on the first write. SQLite is an explicit LOCAL-only boundary,
    NOT an authenticated tamper-proof regulatory audit store.
    """
    if not isinstance(explanation, dict):
        raise ScoringContractError("Research explanation object required")
    transaction_id = explanation.get("transaction_id")
    features = explanation.get("top_features")
    if not isinstance(features, list):
        raise ScoringContractError("Research feature attributions required")
    verified = explain_transaction(
        connection, transaction_id, scorer=scorer, top_k=len(features),
    )
    if explanation != verified:
        raise ScoringContractError("Unverified or mutated SHAP explanation rejected")
    # Save research explanation only after the *same source, feature and model*
    # has a separately verified persisted model score.
    row = connection.execute(
        """SELECT model_sha256, feature_snapshot_sha256,
                  source_payload_sha256, score
           FROM transaction_research_scores
           WHERE transaction_id=? AND manifest_sha256=?""",
        (transaction_id, explanation["manifest_sha256"]),
    ).fetchone() if connection.execute(
        """SELECT name FROM sqlite_master WHERE type='table'
           AND name='transaction_research_scores'"""
    ).fetchone() else None
    if row != (
        explanation["model_sha256"],
        explanation["feature_snapshot_sha256"],
        explanation["source_payload_sha256"],
        explanation["verified_model_probability"],
    ):
        raise ScoringContractError("Matching verified saved research score required")
    canonical = _canonical(explanation)
    digest = _digest(canonical)
    connection.execute(
        """CREATE TABLE IF NOT EXISTS transaction_research_explanations (
            transaction_id TEXT NOT NULL,
            manifest_sha256 TEXT NOT NULL,
            explainer_version TEXT NOT NULL,
            explanation_sha256 TEXT NOT NULL,
            explanation_json TEXT NOT NULL,
            saved_at_utc TEXT NOT NULL,
            PRIMARY KEY(transaction_id, manifest_sha256, explainer_version)
        )"""
    )
    key = (transaction_id, explanation["manifest_sha256"], EXPLAINER_VERSION)
    existing = connection.execute(
        """SELECT explanation_sha256, explanation_json
           FROM transaction_research_explanations
           WHERE transaction_id=? AND manifest_sha256=? AND explainer_version=?""",
        key,
    ).fetchone()
    if existing:
        if existing != (digest, canonical):
            raise ScoringContractError("Refusing to overwrite previously stored explanation")
        return explanation
    connection.execute(
        """INSERT OR IGNORE INTO transaction_research_explanations
           (transaction_id, manifest_sha256, explainer_version,
            explanation_sha256, explanation_json, saved_at_utc)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (*key, digest, canonical, datetime.now(timezone.utc).isoformat()),
    )
    authoritative = connection.execute(
        """SELECT explanation_sha256, explanation_json
           FROM transaction_research_explanations
           WHERE transaction_id=? AND manifest_sha256=? AND explainer_version=?""",
        key,
    ).fetchone()
    if authoritative != (digest, canonical):
        connection.rollback()
        raise ScoringContractError("Concurrent explanation conflict; refusing write")
    connection.commit()
    return explanation
