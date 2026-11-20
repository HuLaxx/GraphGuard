"""Synthetic-only Platt calibration and distribution shift contracts."""

import copy

import numpy as np
import pytest

from ml.monitoring.synthetic_calibration_drift import (
    block_pr_auc_interval,
    drift_psi,
    evaluate_synthetic,
    fit_validation_platt,
)


def test_unchanged_distribution_and_mean_shift():
    base = np.linspace(0.0, 1.0, 40)
    same = drift_psi(base, base)
    shifted = drift_psi(base, base + 10)
    assert same["psi"] == pytest.approx(0.0, abs=1e-12)
    assert shifted["psi"] > same["psi"]
    assert shifted["status"] == "measured_heuristic"


def test_constant_and_invalid_inputs_fail_closed():
    assert drift_psi([1] * 30, [1] * 30)["psi"] is None
    assert drift_psi([1] * 30, [2] * 30)["status"] == "constant_reference_shift_unscored"
    with pytest.raises(ValueError, match="20 observations"):
        drift_psi([1, 2], [1, 2])
    with pytest.raises(ValueError, match="NaN"):
        drift_psi([float("nan")] * 40, [1] * 40)


def test_calibration_never_needs_test_labels():
    y_val = [0] * 20 + [1] * 10
    p_val = np.linspace(0.01, 0.99, 30)
    p_test = np.linspace(0.15, 0.85, 35)
    calibrated_val, calibrated_test, params = fit_validation_platt(y_val, p_val, p_test)
    assert params["method"].startswith("validation_only")
    assert np.all((calibrated_test >= 0) & (calibrated_test <= 1))
    assert np.all((calibrated_val >= 0) & (calibrated_val <= 1))
    with pytest.raises(ValueError):
        fit_validation_platt([0] * 30, p_val, p_test)
    with pytest.raises(ValueError, match="finite"):
        fit_validation_platt(y_val, np.array([float("nan")] * 30), p_test)


def test_block_uncertainty_repeatable_and_requires_both_classes():
    y = [0, 1] * 30
    p = np.linspace(0.02, 0.98, 60)
    assert block_pr_auc_interval(y, p) == block_pr_auc_interval(y, p)
    with pytest.raises(ValueError, match="both classes"):
        block_pr_auc_interval([0] * 60, p)


def test_synthetic_evaluation_is_reproducible_and_contains_no_automatic_decision():
    result = evaluate_synthetic(count=240, seed=42)
    again = evaluate_synthetic(count=240, seed=42)
    assert result == again
    assert result["scope"] == "SYNTHETIC_ONLY_RESEARCH_DO_NOT_DEPLOY"
    assert set(result["rows"]) == {"train", "validation", "test"}
    assert len(result["dataset_sha256"]) == 64
    assert result["raw_test"]["n"] == result["calibrated_test"]["n"]
    assert "selected_model_score_distribution" in result["drift_reference_train_vs_test_psi"]
    assert not {"automatic_alert", "promote", "decision"} & set(result)
