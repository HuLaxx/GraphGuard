"""Pure tests for the model release gate policy. MLflow is not needed here."""
import json

import pytest

from ml.registry.release_gate import evaluate_gate, load_policy, shuffle_train_labels

RECORDED_XGBOOST_TEST = {  # CI run 45093948824 on main, synthetic data.
    "average_precision_pr_auc": 0.7650362977665609,
    "roc_auc": 0.94091796875,
    "recall_at_validation_fpr_threshold": 0.8125,
    "ece_10_bins": 0.06298720091581345,
    "realized_fpr": 0.09375,
}


def test_policy_has_floors_and_ceilings():
    policy = load_policy()
    assert policy["model"] == "xgboost" and policy["split"] == "test"
    assert set(policy["minimums"]) == {"average_precision_pr_auc", "roc_auc", "recall_at_validation_fpr_threshold"}
    assert set(policy["maximums"]) == {"ece_10_bins", "realized_fpr"}
    assert "SYNTHETIC" in policy["scope"]


def test_recorded_baseline_passes():
    result = evaluate_gate(RECORDED_XGBOOST_TEST, load_policy())
    assert result["passed"], result


@pytest.mark.parametrize("metric,value", [
    ("average_precision_pr_auc", 0.2),
    ("roc_auc", 0.55),
    ("recall_at_validation_fpr_threshold", 0.5),
    ("ece_10_bins", 0.3),
    ("realized_fpr", 0.4),
])
def test_any_single_regression_rejects(metric, value):
    degraded = dict(RECORDED_XGBOOST_TEST, **{metric: value})
    result = evaluate_gate(degraded, load_policy())
    assert not result["passed"]
    failed = [c["metric"] for c in result["checks"] if not c["passed"]]
    assert failed == [metric]


def test_boundary_values_pass():
    policy = load_policy()
    edge = dict(RECORDED_XGBOOST_TEST)
    edge.update(policy["minimums"])
    edge.update(policy["maximums"])
    assert evaluate_gate(edge, policy)["passed"]


def test_shuffle_only_touches_train_labels():
    splits = {
        "train": [{"synthetic_label": i % 2, "x": i} for i in range(20)],
        "validation": [{"synthetic_label": 1, "x": 99}],
        "test": [{"synthetic_label": 0, "x": 100}],
    }
    out = shuffle_train_labels(splits, seed=42)
    assert out["validation"] == splits["validation"] and out["test"] == splits["test"]
    assert sorted(r["synthetic_label"] for r in out["train"]) == sorted(r["synthetic_label"] for r in splits["train"])
    assert [r["x"] for r in out["train"]] == [r["x"] for r in splits["train"]]
    assert [r["synthetic_label"] for r in out["train"]] != [r["synthetic_label"] for r in splits["train"]]
