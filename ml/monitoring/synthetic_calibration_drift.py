"""Offline, synthetic-only model calibration and distribution-shift diagnostics.

Fits Platt scaling on a held-out chronological VALIDATION period only.
Never promotes/serves the calibrated model or calls real fraud cases.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score

from ml.training.pit_baselines import (
    FEATURE_COLUMNS,
    chronological_split,
    expected_calibration_error,
    fit_baselines,
    make_synthetic_dataset,
    metrics,
    to_xy,
    validation_threshold,
)

EPSILON = 1e-6
BLOCK_SEED = 20261120


def _probabilities(value):
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 1 or len(array) == 0:
        raise ValueError("Requires non-empty 1D scores")
    if not np.isfinite(array).all() or ((array < 0) | (array > 1)).any():
        raise ValueError("Predicted probabilities must be finite in [0,1]")
    return array


def _logit(proba):
    clipped = np.clip(_probabilities(proba), EPSILON, 1.0 - EPSILON)
    return np.log(clipped / (1.0 - clipped)).reshape(-1, 1)


def fit_validation_platt(y_validation, p_validation, p_test):
    """Calibrate on validation only; no test labels used in fit or threshold."""
    y = np.asarray(y_validation, dtype=np.int64)
    if set(y.tolist()) != {0, 1}:
        raise ValueError("Calibration period requires both classes")
    if len(y) != len(p_validation):
        raise ValueError("Validation labels and scores must align")
    calibrator = LogisticRegression(
        C=1.0, max_iter=500, solver="lbfgs", random_state=BLOCK_SEED
    )
    calibrator.fit(_logit(p_validation), y)
    return (
        calibrator.predict_proba(_logit(p_validation))[:, 1],
        calibrator.predict_proba(_logit(p_test))[:, 1],
        {
            "method": "validation_only_platt_logit_v1",
            "coef": float(calibrator.coef_[0, 0]),
            "intercept": float(calibrator.intercept_[0]),
        },
    )


def drift_psi(reference, current, *, bins=8):
    """Equal-frequency reference PSI; fail closed for nonfinite/small inputs.

    This reports exploratory population shift only. It is not a formal
    significance test, fairness finding, or proof of concept drift.
    """
    ref = np.asarray(reference, dtype=np.float64)
    cur = np.asarray(current, dtype=np.float64)
    if ref.ndim != 1 or cur.ndim != 1 or min(len(ref), len(cur)) < 20:
        raise ValueError("PSI requires at least 20 observations per window")
    if not np.isfinite(ref).all() or not np.isfinite(cur).all():
        raise ValueError("PSI rejects NaN and infinity")
    if np.max(ref) == np.min(ref):
        return {
            "psi": None,
            "status": (
                "constant_reference_no_shift"
                if np.all(cur == ref[0])
                else "constant_reference_shift_unscored"
            ),
        }
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    edges[0] = -np.inf
    edges[-1] = np.inf
    n_bins = len(edges) - 1
    observed = np.histogram(ref, bins=edges)[0]
    compared = np.histogram(cur, bins=edges)[0]
    # Pseudocounts do not validate unrepresentative windows; report sizes.
    a = (observed + 0.5) / (len(ref) + 0.5 * n_bins)
    b = (compared + 0.5) / (len(cur) + 0.5 * n_bins)
    return {
        "psi": float(np.sum((b - a) * np.log(b / a))),
        "status": "measured_heuristic",
    }


def block_pr_auc_interval(y_test, p_test, *, repeats=150, block_size=6):
    """Fixed-seed moving-block test-period bootstrap; descriptive only."""
    y = np.asarray(y_test, dtype=np.int64)
    p = _probabilities(p_test)
    if len(y) != len(p) or len(y) < 20 or set(y.tolist()) != {0, 1}:
        raise ValueError("Uncertainty sample needs both classes and 20+ rows")
    n = len(y)
    width = min(block_size, n)
    rng = np.random.default_rng(BLOCK_SEED)
    values = []
    for _ in range(repeats):
        idx = []
        while len(idx) < n:
            start = int(rng.integers(0, n - width + 1))
            idx.extend(range(start, start + width))
        chosen = np.asarray(idx[:n], dtype=np.int64)
        if len(set(y[chosen].tolist())) == 2:
            values.append(float(average_precision_score(y[chosen], p[chosen])))
    if len(values) < repeats // 2:
        return {"interval": None, "valid_resamples": len(values)}
    return {
        "interval": [float(x) for x in np.quantile(values, [0.025, 0.975])],
        "valid_resamples": len(values),
    }


def evaluate_synthetic(*, count=720, seed=42) -> dict:
    rows = make_synthetic_dataset(count=count, seed=seed)
    parts = chronological_split(rows)
    trained = fit_baselines(parts, seed=seed)
    selected = trained["selected_by_validation_pr_auc"]
    model = trained["models"][selected]
    x_train, _ = to_xy(parts["train"])
    x_val, y_val = to_xy(parts["validation"])
    x_test, y_test = to_xy(parts["test"])
    raw_val = model.predict_proba(x_val)[:, 1]
    raw_test = model.predict_proba(x_test)[:, 1]
    calibrated_val, calibrated_test, cal = fit_validation_platt(
        y_val, raw_val, raw_test
    )
    raw_threshold = validation_threshold(y_val, raw_val)
    calibrated_threshold = validation_threshold(y_val, calibrated_val)
    raw_scores = metrics(y_test, raw_test, raw_threshold)
    calibrated_scores = metrics(y_test, calibrated_test, calibrated_threshold)
    drift = {
        feature: {
            **drift_psi(x_train[:, idx], x_test[:, idx]),
            "reference_count": len(x_train),
            "current_count": len(x_test),
        }
        for idx, feature in enumerate(FEATURE_COLUMNS)
    }
    drift["selected_model_score_distribution"] = {
        **drift_psi(model.predict_proba(x_train)[:, 1], raw_test),
        "reference_count": len(x_train),
        "current_count": len(x_test),
    }
    test_users = {row["user_id"] for row in parts["test"]}
    earlier_users = {row["user_id"] for s in ("train", "validation") for row in parts[s]}
    return {
        "version": "synthetic_calibration_shift_v1",
        "scope": "SYNTHETIC_ONLY_RESEARCH_DO_NOT_DEPLOY",
        "dataset_sha256": hashlib.sha256(
            b"".join(
                json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
                + b"\n"
                for row in rows
            )
        ).hexdigest(),
        "seed": seed,
        "rows": {k: len(v) for k, v in parts.items()},
        "model": selected,
        "selection_policy": "validation PR-AUC, prior to calibration",
        "calibration": cal,
        "raw_test": raw_scores,
        "calibrated_test": calibrated_scores,
        "val_brier_before_calibration": trained["results"][selected]["validation"][
            "brier_score"
        ],
        "val_ece_after_platt_fit_optimistic": expected_calibration_error(
            y_val, calibrated_val
        ),
        "pr_auc_interval_heuristic": block_pr_auc_interval(y_test, calibrated_test),
        "drift_reference_train_vs_test_psi": drift,
        "new_test_users_not_seen_before": len(test_users - earlier_users),
        "limitations": [
            "Original generated labels are not observed fraud outcomes.",
            "Validation-calibration fit and threshold reuse validation data; its fitted ECE is optimistic.",
            "Test metrics are descriptive only; no model/threshold tuning on test.",
            "PSI thresholds are NOT used for automatic action, retraining or case judgment.",
            "Zero new users means cold-start generalization is not measured.",
            "Block-bootstrap PR-AUC percentiles are small-sample heuristics, not guaranteed confidence.",
            "Never auto-promote or rollback a model based on this synthetic report.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=720)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = evaluate_synthetic(count=args.count, seed=args.seed)
    content = (json.dumps(report, sort_keys=True, allow_nan=False, indent=2) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as handle:
        handle.write(content)
    print(json.dumps({
        "report_sha256": hashlib.sha256(content).hexdigest(),
        "model": report["model"],
        "raw_test_ap": report["raw_test"]["average_precision_pr_auc"],
        "calibrated_test_ap": report["calibrated_test"]["average_precision_pr_auc"],
        "raw_test_fpr": report["raw_test"]["realized_fpr"],
        "calibrated_test_fpr": report["calibrated_test"]["realized_fpr"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
