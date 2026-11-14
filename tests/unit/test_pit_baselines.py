"""Reproducibility and leakage-policy tests for synthetic-only pit-v1 ML.

No external dataset, live customers, Kafka/Neo4j or AWS is involved.
"""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from ml.training.pit_baselines import (
    FEATURE_COLUMNS, FEATURE_VERSION, FPR_LIMIT,
    chronological_split, expected_calibration_error, fit_baselines,
    make_synthetic_dataset, metrics, run_experiment, to_xy,
    validation_threshold,
)


@pytest.fixture(scope="module")
def synthetic_rows():
    return make_synthetic_dataset(count=240, seed=42)


def test_generated_dataset_is_bitwise_reproducible_without_external_data(synthetic_rows):
    repeated = make_synthetic_dataset(count=240, seed=42)
    assert repeated == synthetic_rows
    assert repeated != make_synthetic_dataset(count=240, seed=43)
    assert all(row["feature_version"] == FEATURE_VERSION for row in repeated)
    assert all("synthetic_label" not in row["features"] for row in repeated)
    assert all("user_id" not in row["features"] for row in repeated)
    assert all("fraud" not in str(row["features"]).lower() for row in repeated)
    assert all(set(row["features"]) == set(FEATURE_COLUMNS) for row in repeated)


def test_strict_time_splits_and_id_overlap_guards(synthetic_rows):
    parts = chronological_split(synthetic_rows)
    assert sum(len(part) for part in parts.values()) == len(synthetic_rows)
    assert parts["train"][-1]["timestamp_ms"] < parts["validation"][0]["timestamp_ms"]
    assert parts["validation"][-1]["timestamp_ms"] < parts["test"][0]["timestamp_ms"]
    assert not ({r["transaction_id"] for r in parts["train"]} & {r["transaction_id"] for r in parts["test"]})
    assert all(set(r["synthetic_label"] for r in part) == {0, 1} for part in parts.values())

    rows = copy.deepcopy(synthetic_rows)
    a, b = int(len(rows) * 0.65), int(len(rows) * 0.80)
    rows[a]["timestamp_ms"] = rows[a - 1]["timestamp_ms"]
    with pytest.raises(ValueError, match="overlapping event-time"):
        chronological_split(rows)

    rows = copy.deepcopy(synthetic_rows)
    rows[-1]["transaction_id"] = rows[0]["transaction_id"]
    with pytest.raises(ValueError, match="Identity overlap"):
        chronological_split(rows)


def test_explicit_allowlist_rejects_label_identity_or_feature_version(synthetic_rows):
    row = copy.deepcopy(synthetic_rows[0])
    row["features"]["is_fraud"] = 1
    with pytest.raises(ValueError, match="allowlist"):
        to_xy([row])

    row = copy.deepcopy(synthetic_rows[0])
    row["feature_version"] = "future-leaky-features"
    with pytest.raises(ValueError, match="version"):
        to_xy([row])

    row = copy.deepcopy(synthetic_rows[0])
    row["features"].pop("device_other_users_7d")
    with pytest.raises(ValueError, match="allowlist"):
        to_xy([row])


def test_threshold_is_validation_only_and_respects_fpr_budget():
    y = np.array([0] * 100 + [1] * 10, dtype=np.int64)
    probabilities = np.linspace(0.01, 0.99, len(y))
    threshold = validation_threshold(y, probabilities, FPR_LIMIT)
    actual = np.mean(probabilities[y == 0] > threshold)
    assert actual <= FPR_LIMIT
    assert 0.0 <= expected_calibration_error(y, probabilities) <= 1.0
    report = metrics(y, probabilities, threshold, k=15)
    assert report["precision_at_k_count"] == 15
    assert report["realized_fpr"] <= FPR_LIMIT
    assert 0 <= report["average_precision_pr_auc"] <= 1
    assert 0 <= report["brier_score"] <= 1


def test_held_out_labels_do_not_affect_training_or_model_selection(synthetic_rows):
    parts = chronological_split(synthetic_rows)
    baseline = fit_baselines(parts, seed=42)

    # A holdout outcome is not part of training or model selection.
    amended = copy.deepcopy(parts)
    amended["test"][0]["synthetic_label"] ^= 1
    rerun = fit_baselines(amended, seed=42)
    assert baseline["selected_by_validation_pr_auc"] == rerun["selected_by_validation_pr_auc"]
    assert baseline["results"]["logistic_regression"]["validation"] == rerun["results"]["logistic_regression"]["validation"]
    assert baseline["results"]["xgboost"]["validation"] == rerun["results"]["xgboost"]["validation"]
    for model in ("logistic_regression", "xgboost"):
        x, _ = to_xy(parts["test"])
        assert np.allclose(
            baseline["models"][model].predict_proba(x),
            rerun["models"][model].predict_proba(x),
        )


def test_persisted_artifacts_are_hash_checked_and_no_pickle(tmp_path):
    out = tmp_path / "synthetic-baselines"
    report = run_experiment(out, count=240, seed=42)
    assert report["scope"].startswith("SYNTHETIC ONLY")
    assert report["dataset_rows"] == 240
    assert set(report["evaluation"]) == {"logistic_regression", "xgboost"}
    assert report["selected_by_validation_pr_auc"] in report["evaluation"]
    assert report["feature_columns"] == list(FEATURE_COLUMNS) or tuple(report["feature_columns"]) == FEATURE_COLUMNS
    assert report["train_validation_test"]["train"]["last_utc_ms"] < report["train_validation_test"]["validation"]["first_utc_ms"]
    for name, expected in report["artifacts_sha256"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((out / "synthetic_records.jsonl").read_bytes()).hexdigest() == report["dataset_sha256"]
    assert json.loads((out / "manifest.json").read_text())["dataset_sha256"] == report["dataset_sha256"]
    assert not list(out.glob("*.pkl"))
    assert not list(out.glob("*.joblib"))

    # Deterministic synthetic generator and model configuration; compare data
    # hashes, not native model bytes that can change across library versions.
    rerun = run_experiment(tmp_path / "rerun", count=240, seed=42)
    assert rerun["dataset_sha256"] == report["dataset_sha256"]
    assert rerun["selected_by_validation_pr_auc"] == report["selected_by_validation_pr_auc"]
    assert rerun["evaluation"] == report["evaluation"]
