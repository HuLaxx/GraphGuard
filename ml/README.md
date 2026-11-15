# GraphGuard — ML engineering (evidence-gated)

The current verified path is a **synthetic, local decision-support research experiment**, not a commercial fraud detection system. A numerical score or SHAP attribution does **not** establish that a person or payment is fraudulent.

## Measured, tested capabilities (stacked draft PRs, not merged)

| Capability | Evidence and limits |
| --- | --- |
| Durable Avro/Schema Registry → Kafka → Neo4j | Disposable synthetic fixtures, recovery and replay [PR #4](https://github.com/HuLaxx/GraphGuard/pull/4) |
| Immutable point-in-time graph-context features | Event-time and first-observed-time cutoffs, local SQLite [PR #5](https://github.com/HuLaxx/GraphGuard/pull/5) |
| Logistic + XGBoost baseline training | Deterministic, chronologically split synthetic labels with measured scores and SHA-256 artifacts [PR #6](https://github.com/HuLaxx/GraphGuard/pull/6); see [synthetic baseline evidence](../docs/SYNTHETIC_BASELINES.md) |
| Hash-pinned synthetic model scoring | Requires the trusted model-manifest digest, accepted source/feature hash and feature version [PR #7](https://github.com/HuLaxx/GraphGuard/pull/7); see [verified scoring](../docs/VERIFIED_SYNTHETIC_SCORING.md) |
| **True model-derived SHAP attribution** | XGBoost's native exact TreeSHAP in **log odds** and analytic linear-model Shapley, with reconstruction and replay tests [PR #8](https://github.com/HuLaxx/GraphGuard/pull/8); see [attribution evidence](../docs/VERIFIED_SHAP.md) |

**SHAP is an attribution of the trained model's behavior, not a causal explanation of fraud.** Existing synthetic XGBoost holdout false-positive rate was 9.375%, exceeding its 5% validation target. No automated account/payment decisions are supported.

## Experimental/unfinished components

- The old `training/baseline_xgboost.py` / `train_xgboost_rigorous.py` and `training/create_dataset.py` use different feature definitions or historical joins and have **not** been certified as leakage-safe.
- `training/gat_model.py` contains an implementation, but graph sampling, reproducible training, validation and comparison with tabular baselines remain **unverified**. No GAT accuracy or GAT-in-production claim.
- `training/ensemble_model.py` is not a verified real-data ensemble. Its fixed weights are not evidence of optimization.
- `serving/api.py` is a legacy, separate API/feature namespace. This release does **not** assert that it loads the `pit-v1` model, runs real SHAP, authenticates reviewers or persists a human-reviewed fraud case.
- MLflow experiment provenance, registry approval/rollback, model drift, public dataset evaluation, cold-start entities, production observability and independent cloud cost governance remain future work.

## Reproduce and review

```bash
python -m pip install -r requirements-ml-ci.txt
python -m pytest tests/unit/test_pit_baselines.py \
  tests/unit/test_verified_pit_scorer.py \
  tests/unit/test_verified_shap.py -v
```

For verified model/artifact evidence, see the [evidence register](../docs/EVIDENCE_REGISTER.md) and [P0–P4 release checklist](../docs/ENGINEERING_RELEASE_CHECKLIST.md). No stacked draft PR should be represented as merged or production deployed.
