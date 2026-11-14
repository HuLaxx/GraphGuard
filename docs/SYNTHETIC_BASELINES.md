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

## Measured evidence — CI 43611311872 (14 November 2026)

**Exact training code SHA:** `462e7c682bedd2595f672ef09f21d8333f06a114`; [GitHub Actions run](https://github.com/HuLaxx/GraphGuard/actions/runs/43611311872). All 7 jobs passed; 6 dedicated ML unit tests passed and the generated artifacts were uploaded.

| Synthetic held-out test metric (144 transactions, 16 positive) | Logistic regression | XGBoost |
| --- | ---: | ---: |
| Average precision / PR-AUC | 0.6887 | 0.7650 |
| ROC-AUC | 0.9072 | 0.9409 |
| Precision@25 | 0.52 | 0.52 |
| Recall at validation-selected operating threshold | 0.7500 | 0.8125 |
| Realized false-positive rate | 0.0625 | 0.09375 |
| Brier score, lower is better | 0.0824 | 0.0695 |
| Ten-bin ECE, lower is better | 0.1120 | 0.0630 |

Selected model by validation PR-AUC: **XGBoost** (validation AP 0.8786 vs 0.8328 for logistic regression). These numbers are **specific to this generator, fixed seed, fixed period and dependency versions**. A 5% validation FPR target is **not maintained on test**; neither model should be promoted based on these synthetic figures.

Source dataset SHA-256:
`100b3ef3ae97ef7ea0d040de0bdbe31a6109cfe39f958d66eb3aeec57f0d3306`

Model SHA-256: logistic `35acf88762b6f54701f1d2453876b74b3fb9fca39b4dfa3d09d097d11235aece`; XGBoost `87e40983a9294b60b3441c41f7c3c79ea1d0f7461d032cb6f429f1129a43a20e`.

The CI artifact `graphguard-pit-ml-synthetic-baselines` includes both models, the synthetic records and full manifest. No deployed inference endpoint or registered production model exists.
