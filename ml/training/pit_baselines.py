"""Reproducible, synthetic-only GraphGuard fraud baseline experiment.

Run: python -m ml.training.pit_baselines --output-dir .local/ml-baselines
Do not publish synthetic benchmark scores as real-world fraud performance.
No network, provider data, learned embedding or external dataset is used.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import tempfile

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score, brier_score_loss, roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parents[2]
CONSUMERS = ROOT / "data-eng" / "consumers"
if str(CONSUMERS) not in sys.path:
    sys.path.insert(0, str(CONSUMERS))

from transaction_ledger import TransactionLedger
from point_in_time_features import PointInTimeFeatureStore, FEATURE_VERSION

SEED = 42
GENERATOR_VERSION = "synthetic-ml-v1"
MODEL_INPUT_VERSION = "pit-v1+current-amount-v1"
HOUR_MS = 3_600_000
BASE_MS = 1_767_225_600_000  # Fixed UTC time. Never infer from the CI system clock.
FPR_LIMIT = 0.05
PRECISION_K = 25

# No IDs, outcomes, fraud flags, future aggregates, post-investigation fields,
# model scores, source rowid or timestamps are model feature columns.
FEATURE_COLUMNS = (
    "user_txn_count_24h",
    "user_same_currency_txn_count_24h",
    "user_same_currency_amount_sum_24h",
    "user_same_currency_amount_avg_24h",
    "merchant_txn_count_24h",
    "device_txn_count_7d",
    "device_distinct_users_7d",
    "device_other_users_7d",
    "merchant_distinct_users_7d",
    "user_merchant_txn_count_30d",
    "user_distinct_devices_30d",
    "current_amount",
)


def canonical(data) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_synthetic_dataset(count: int = 720, seed: int = SEED) -> list[dict]:
    """Synthetic transaction labels held OUTSIDE the persisted source ledger.

    Latent scenarios affect amounts/merchant/device selection, so the task is
    illustrative rather than an independent measure of genuine fraud quality.
    Time/IDs are deterministic, and each event is snapshotted at first receipt.
    """
    if count < 120:
        raise ValueError("Use >=120 synthetic events for a meaningful three-way split")
    rng = random.Random(seed)
    rows = []
    with tempfile.TemporaryDirectory(prefix="graphguard-synthetic-") as directory:
        ledger = TransactionLedger(str(Path(directory) / "ledger.sqlite3"))
        store = PointInTimeFeatureStore(ledger.connection)
        try:
            for i in range(count):
                label = int(rng.random() < 0.12)
                user = rng.randrange(32)
                # Simulated scenarios overlap deliberately: no label is a
                # direct feature and legitimate payments can share a device.
                shared = rng.random() < (0.7 if label else 0.08)
                device = (f"synthetic-shared-{rng.randrange(4)}" if shared
                          else f"synthetic-device-{user % 27}")
                merchant = (f"synthetic-risk-merchant-{rng.randrange(3)}"
                            if rng.random() < (0.66 if label else 0.21)
                            else f"synthetic-merchant-{rng.randrange(15)}")
                amount = round(
                    rng.uniform(40, 460) if label else rng.uniform(8, 280),
                    2,
                )
                event_id = f"synthetic-ml-txn-{i:06d}"
                event = {
                    "transaction_id": event_id,
                    "user_id": f"synthetic-user-{user:03d}",
                    "merchant_id": merchant,
                    "device_id": device,
                    "amount": amount,
                    "currency": "GBP",
                    "timestamp": BASE_MS + i * HOUR_MS,
                    "schema_version": 1,
                    "idempotency_key": sha256(event_id.encode("utf-8")),
                }
                receipt = ledger.record(event, topic="synthetic.ml.baseline", partition=0, offset=i)
                if receipt.status != "new":
                    raise RuntimeError("Synthetic generator produced a duplicate ID")
                snap = store.snapshot_for(event_id)
                features = dict(snap["features"])
                if set(features) != set(FEATURE_COLUMNS) - {"current_amount"}:
                    raise RuntimeError("pit-v1 feature contract changed; retraining must be reviewed")
                if snap["event_time_ms"] != event["timestamp"]:
                    raise RuntimeError("Feature snapshot is not aligned to source event")
                features["current_amount"] = amount  # Known at decision time.
                if not all(type(value) in (int, float) and math.isfinite(value) for value in features.values()):
                    raise RuntimeError("Invalid model input")
                rows.append({
                    "transaction_id": event_id,
                    "timestamp_ms": event["timestamp"],
                    "user_id": event["user_id"],  # Audit only, never an ML column.
                    "device_id": event["device_id"],  # Audit only.
                    "feature_version": FEATURE_VERSION,
                    "features": features,
                    "synthetic_label": label,  # Never included in the ledger or features.
                })
        finally:
            ledger.close()
    return rows


def chronological_split(rows: list[dict]) -> dict[str, list[dict]]:
    """Strict event-time, non-overlapping 65/15/20 train/val/test split."""
    rows = sorted(rows, key=lambda row: (row["timestamp_ms"], row["transaction_id"]))
    n = len(rows)
    a, b = int(n * 0.65), int(n * 0.80)
    if a == 0 or b <= a or b >= n:
        raise ValueError("Not enough rows for three distinct periods")
    splits = {"train": rows[:a], "validation": rows[a:b], "test": rows[b:]}
    times = [[r["timestamp_ms"] for r in part] for part in splits.values()]
    if not (max(times[0]) < min(times[1]) and max(times[1]) < min(times[2])):
        raise ValueError("Tied or overlapping event-time windows; cannot guarantee chronology")
    keys = [[r["transaction_id"] for r in part] for part in splits.values()]
    if len({key for part in keys for key in part}) != n:
        raise ValueError("Identity overlap: a transaction occurs in multiple splits")
    for name, part in splits.items():
        labels = [r["synthetic_label"] for r in part]
        if set(labels) != {0, 1}:
            raise ValueError(f"{name} split must contain both classes")
    return splits


def to_xy(rows: list[dict]):
    for row in rows:
        if row["feature_version"] != FEATURE_VERSION or set(row["features"]) != set(FEATURE_COLUMNS):
            raise ValueError("Feature version or allowlist mismatch")
        if "synthetic_label" in row["features"] or "user_id" in row["features"]:
            raise ValueError("Target/identity leakage into model features")
    matrix = np.asarray([
        [row["features"][key] for key in FEATURE_COLUMNS] for row in rows
    ], dtype=np.float64)
    if not np.isfinite(matrix).all():
        raise ValueError("Non-finite feature input")
    return matrix, np.asarray([r["synthetic_label"] for r in rows], dtype=np.int64)


def validation_threshold(y_validation, probabilities, fpr_limit=FPR_LIMIT) -> float:
    """Choose threshold only using validation negatives, with FPR <= budget."""
    negatives = sorted(
        (float(p) for y, p in zip(y_validation, probabilities) if int(y) == 0),
        reverse=True,
    )
    if not negatives:
        raise ValueError("Validation negative class required for threshold selection")
    max_fp = int(math.floor(fpr_limit * len(negatives)))
    if max_fp >= len(negatives):
        return 0.0
    # Predict positive strictly ABOVE threshold, preserving FPR even for ties.
    return float(negatives[max_fp])


def expected_calibration_error(y_true, proba, bins=10) -> float:
    """Equal-width diagnostic, not a calibrated probability guarantee."""
    y_true = np.asarray(y_true)
    proba = np.asarray(proba)
    total = 0.0
    for j in range(bins):
        lo, hi = j / bins, (j + 1) / bins
        mask = (proba >= lo) & ((proba <= hi) if j == bins - 1 else (proba < hi))
        if np.any(mask):
            total += float(mask.mean()) * abs(float(y_true[mask].mean()) - float(proba[mask].mean()))
    return float(total)


def metrics(y_true, proba, threshold: float, k: int = PRECISION_K) -> dict:
    """All counts and thresholds are reported; never optimize on the test labels."""
    y = np.asarray(y_true, dtype=np.int64)
    p = np.asarray(proba, dtype=np.float64)
    if y.ndim != 1 or p.shape != y.shape or set(y.tolist()) != {0, 1}:
        raise ValueError("Both classes and equal-length one-dimensional predictions required")
    if not np.isfinite(p).all() or np.any(p < 0) or np.any(p > 1):
        raise ValueError("Invalid probabilities")
    chosen = p > threshold
    top_k = min(k, len(y))
    top = np.argsort(-p, kind="stable")[:top_k]
    negatives = y == 0
    positives = y == 1
    return {
        "n": int(len(y)),
        "positives": int(positives.sum()),
        "prevalence": float(positives.mean()),
        "average_precision_pr_auc": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier_score": float(brier_score_loss(y, p)),
        "ece_10_bins": expected_calibration_error(y, p),
        "precision_at_k": float(y[top].mean()),
        "precision_at_k_count": int(top_k),
        "recall_at_validation_fpr_threshold": float(chosen[positives].mean()),
        "realized_fpr": float(chosen[negatives].mean()),
        "threshold_selected_on_validation": float(threshold),
    }


def split_audit(splits: dict[str, list[dict]]) -> dict:
    """Report repeated entities; their ID values are NOT model inputs.

    Repeated users/devices across periods are expected in the same live stream.
    We do not claim entity-disjoint evaluation; a cold-start benchmark is next.
    """
    result = {}
    prior_users, prior_devices = set(), set()
    for name, period in splits.items():
        users = {row["user_id"] for row in period}
        devices = {row["device_id"] for row in period}
        result[name] = {
            "count": len(period),
            "positives": sum(row["synthetic_label"] for row in period),
            "first_utc_ms": period[0]["timestamp_ms"],
            "last_utc_ms": period[-1]["timestamp_ms"],
            "prior_seen_user_overlap": len(users & prior_users),
            "prior_seen_device_overlap": len(devices & prior_devices),
        }
        prior_users |= users
        prior_devices |= devices
    return result


def fit_baselines(splits: dict[str, list[dict]], seed: int = SEED) -> dict:
    """Fit train-only pipelines; choose the winner using validation PR-AUC."""
    x_train, y_train = to_xy(splits["train"])
    x_val, y_val = to_xy(splits["validation"])
    x_test, y_test = to_xy(splits["test"])
    weight = float((y_train == 0).sum() / (y_train == 1).sum())
    models = {
        "logistic_regression": make_pipeline(
            StandardScaler(),
            LogisticRegression(
                max_iter=1000, class_weight="balanced", random_state=seed,
                solver="lbfgs",
            ),
        ),
        "xgboost": XGBClassifier(
            n_estimators=90,
            max_depth=3,
            learning_rate=0.08,
            subsample=1.0,
            colsample_bytree=1.0,
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            scale_pos_weight=weight,
            n_jobs=1,
            random_state=seed,
        ),
    }
    results = {}
    for name, model in models.items():
        model.fit(x_train, y_train)  # No test/validation labels in fit().
        val_prob = model.predict_proba(x_val)[:, 1]
        threshold = validation_threshold(y_val, val_prob)
        test_prob = model.predict_proba(x_test)[:, 1]
        results[name] = {
            "validation": metrics(y_val, val_prob, threshold),
            "test": metrics(y_test, test_prob, threshold),
        }
    selected = max(
        results, key=lambda name: (results[name]["validation"]["average_precision_pr_auc"], name)
    )
    return {
        "models": models,
        "results": results,
        "selected_by_validation_pr_auc": selected,
        "split_audit": split_audit(splits),
        "train_negative_to_positive_weight": weight,
    }


def export_artifacts(rows: list[dict], trained: dict, output_dir: Path, seed: int) -> dict:
    """Emit auditable self-contained artifacts without unsafe model pickle files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = b"".join(canonical(row) + b"\n" for row in rows)
    dataset_path = output_dir / "synthetic_records.jsonl"
    dataset_path.write_bytes(samples)
    logistic = trained["models"]["logistic_regression"]
    scaler = logistic.named_steps["standardscaler"]
    classifier = logistic.named_steps["logisticregression"]
    logistic_path = output_dir / "logistic_baseline.json"
    logistic_path.write_bytes(canonical({
        "model_type": "standard_scaler_plus_logistic",
        "feature_columns": FEATURE_COLUMNS,
        "input_version": MODEL_INPUT_VERSION,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "coefficients": classifier.coef_[0].tolist(),
        "intercept": classifier.intercept_.tolist(),
    }) + b"\n")
    xgb_path = output_dir / "xgboost_baseline.json"
    trained["models"]["xgboost"].save_model(xgb_path)

    # A fresh, trusted model load must reproduce the trained probabilities.
    reloaded = XGBClassifier()
    reloaded.load_model(xgb_path)
    dataset_splits = chronological_split(rows)
    test_x, _ = to_xy(dataset_splits["test"])
    if not np.allclose(
        reloaded.predict_proba(test_x),
        trained["models"]["xgboost"].predict_proba(test_x),
        atol=1e-8, rtol=1e-8,
    ):
        raise RuntimeError("Saved XGBoost model could not reproduce test predictions")

    manifest = {
        "scope": "SYNTHETIC ONLY - not real bank fraud detection",
        "data_source": "deterministic in-repo synthetic generator, no external dataset",
        "generator_version": GENERATOR_VERSION,
        "feature_version": FEATURE_VERSION,
        "model_input_version": MODEL_INPUT_VERSION,
        "feature_columns": FEATURE_COLUMNS,
        "seed": seed,
        "dataset_rows": len(rows),
        "dataset_sha256": sha256(samples),
        "train_validation_test": trained["split_audit"],
        "split_policy": "strict chronological 65/15/20; feature snapshots use prior event time and first observation order",
        "entity_overlap_policy": "repeated entity IDs audited, excluded from model features; not entity-disjoint",
        "class_balance_policy": "balanced LR and train-only XGBoost negative/positive weight; no SMOTE",
        "train_negative_to_positive_weight": trained["train_negative_to_positive_weight"],
        "selection_policy": "validation average precision (PR-AUC), single fixed hyperparameter configuration per model",
        "selected_by_validation_pr_auc": trained["selected_by_validation_pr_auc"],
        "evaluation": trained["results"],
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "sklearn": __import__("sklearn").__version__,
            "xgboost": __import__("xgboost").__version__,
        },
        "artifacts_sha256": {
            logistic_path.name: sha256(logistic_path.read_bytes()),
            xgb_path.name: sha256(xgb_path.read_bytes()),
        },
        "limitations": [
            "Simulated labels and latent synthetic patterns are not external validation.",
            "Temporal entity overlap remains; results do not measure cold-start generalization.",
            "No trained model is connected to API, SHAP, MLflow registry or analyst decisions.",
            "Brier/ECE are diagnostics, not proof of calibrated probabilities or fairness.",
            "No independent external dataset license or real-world accuracy is claimed.",
        ],
    }
    (output_dir / "manifest.json").write_bytes(canonical(manifest) + b"\n")
    return manifest


def run_experiment(output_dir: Path, *, count: int = 720, seed: int = SEED) -> dict:
    rows = make_synthetic_dataset(count=count, seed=seed)
    splits = chronological_split(rows)
    trained = fit_baselines(splits, seed=seed)
    return export_artifacts(rows, trained, output_dir, seed=seed)


def main():
    parser = argparse.ArgumentParser(description="Synthetic-only GraphGuard baseline evaluation")
    parser.add_argument("--count", type=int, default=720)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output-dir", type=Path, default=Path(".local/ml-baselines"))
    args = parser.parse_args()
    report = run_experiment(args.output_dir, count=args.count, seed=args.seed)
    print(json.dumps({
        "scope": report["scope"],
        "rows": report["dataset_rows"],
        "dataset_sha256": report["dataset_sha256"],
        "selected_by_validation_pr_auc": report["selected_by_validation_pr_auc"],
        "evaluation": report["evaluation"],
        "artifact_sha256": report["artifacts_sha256"],
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
