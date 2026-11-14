# GraphGuard P1/P2 — Reproducible baseline experiment (synthetic only)

**Status:** research/demo experiment; not production fraud accuracy, bank data,
trained API scoring, deployed SHAP, GAT readiness, or live customer cases.

## Purpose and provenance

The experiment in `ml/training/pit_baselines.py` trains both logistic
regression and XGBoost using the real `pit-v1` historical feature store.
It uses in-repo deterministic **synthetic-only** data (seed 42; generator
`synthetic-ml-v1`), with no downloaded third-party dataset, real
fraud labels, provider API, paid AWS service or MLflow server. Synthetic
labels are simulated scenarios, NOT confirmed wrongdoing. No external
dataset licence is claimed; the repository's overall source licence
requires a separate review.

## Leakage and split controls

1. Each synthetic event is written via `TransactionLedger.record` and
   snapshotted immediately by `PointInTimeFeatureStore.snapshot_for`.
   The generator's synthetic label stays **outside** the source ledger.
2. An explicit allowlist contains 11 `pit-v1` historical features
   plus current amount (known at decision time). Input version:
   `pit-v1+current-amount-v1`. No IDs, future outcomes, targets,
   source rowids or human-review labels enter the model.
3. Train/validation/test = strict chronological 65/15/20. Duplicate
   IDs, tied boundary timestamps or single-class splits fail closed.
   Entities may reappear across periods, which models the same customer
   returning in a stream; IDs are excluded from features. Audit records
   entity overlaps. **This is not an entity-disjoint cold-start test.**
4. Logistic standardization and class balancing are trained on train only;
   XGBoost weighting uses train-only prevalence. No SMOTE or global
   normalization. Both models have fixed disclosed hyperparameters.
5. Winner = maximum *validation* average precision (PR-AUC). Decision
   threshold is selected using validation negatives to respect an FPR
   budget of 5%. Never select on the test set.

## Inspectable measurements

Each validation and test result includes average precision/PR-AUC,
ROC-AUC, Brier score, 10-bin expected calibration error, precision@25,
recall at validation-selected FPR, realized FPR and class prevalence.
These are diagnostics, not claims of calibrated, fair or generalizable
real-world fraud decisions. **No model metrics are predeclared**: use
the precise CI-run artefact and log, not numbers in a proposal.

The generated manifest reports generator/version, dataset SHA-256, model
JSON hashes, seed, feature columns, installed Python/numpy/sklearn/XGBoost
versions, chronological split dates, entity overlap counts and scores.

## Reproduce (Python 3.11, CPU only)

```bash
python -m pip install -r requirements-ml-ci.txt
python -m pytest tests/unit/test_pit_baselines.py -v
python -m ml.training.pit_baselines \
    --count 720 --seed 42 --output-dir .local/ml-baselines
```

Local generated files in `.local/ml-baselines` are ignored by Git:
- `synthetic_records.jsonl`: inspectable synthetic dataset, with
  synthetic labels ONLY for offline evaluation;
- `logistic_baseline.json`: safe JSON scaler coefficients and input order
  (not executable pickle);
- `xgboost_baseline.json`: native XGBoost artifact, reloaded in a smoke test;
- `manifest.json`: hashes and measured validation/test metrics.

CI's `Synthetic point-in-time ML baselines` job runs the tests and
experiment and uploads the synthetic-only artifacts for 14 days. Those
artifacts are not deployed.

## Independent legacy pipeline caveats

The existing `ml/training/create_dataset.py` uses rolling features
which may include the scored transaction and profile/graph joins without
a first-observed-time gate. Its leakage risk must be handled separately.
The existing rigorous XGBoost and GAT implementations are NOT validated
by this PR. Existing `ml/serving/api.py` uses a different feature
namespace and may return fallbacks; do not silently deploy a model trained
on `pit-v1` into that API. Heuristic explanations are not SHAP.

## Remaining gates

The dataset is artificial and cannot prove real-fraud performance or
fairness. Need a documented/licensed public dataset, cold-start analysis,
temporal validation over multiple periods, sample uncertainty, calibrated
predictions if used for decisions, and human-review feedback.
Next milestone is **versioned source-to-model scoring** with actual model
hash checks and measured SHAP, followed by authenticated case audit.
