# GraphGuard P1 — Trust-pinned synthetic feature → model inference

**Scope:** reproducible local research workflow, not a bank fraud classifier in production. No automated denial, accusation, real customer information, hosted API, SHAP or human case decision is implemented by this milestone.

## Inference boundary

1. A transaction must first be accepted by the real Kafka Avro consumer and materialized in the SQLite first-seen source ledger. `GraphBuilder` writes its `pit-v1` feature snapshot before committing the Kafka source offset.
2. A separately trained synthetic Logistic Regression/XGBoost artifact and `manifest.json` are produced by the PR #6 baseline experiment. The caller must pass the **trusted 64-character SHA-256 of the manifest** obtained through an approved build/CI channel. Calculating the pin from an untrusted manifest at score time is **not a trust boundary**.
3. `VerifiedSyntheticScorer` verifies manifest SHA-256, exact synthetic scope, selected model artifact SHA-256, feature column ordering and input version `pit-v1+current-amount-v1`, then loads the native XGBoost or safe JSON logistic model. No pickle or arbitrary code loader is used.
4. Each inference verifies accepted source payload hash, schema version, GBP-only synthetic scope, immutable feature-snapshot hash, original receipt/event-time cutoffs, feature version and the exact 11 historical numeric features. Current amount comes only from the accepted source payload. Any mismatch **fails closed**.
5. A numeric model score is returned with model name, artifact/manifest/source/feature hashes, feature version and `RESEARCH_SCORE_ONLY_NO_AUTOMATED_DECISION`. The score is an **uncalibrated synthetic model output**, never proof of wrongdoing. Optional `save_research_score` first **recalculates the proposed score with a verified pinned scorer**, then appends one local research record per transaction+manifest. Unverified first writes and attempts to overwrite a previous score are rejected; replay is idempotent.

## Reproduce

CPU-only unit tests and model artifacts (Python 3.11):

```bash
python -m pip install -r requirements-ml-ci.txt
python -m pytest tests/unit/test_pit_baselines.py tests/unit/test_verified_pit_scorer.py -v
python -m ml.training.pit_baselines --count 720 --seed 42 --output-dir .local/ml-baselines
sha256sum .local/ml-baselines/manifest.json
```

After ingesting a **synthetic** Kafka transaction into the local `.local/transaction-ledger.sqlite3`, pass the independently verified manifest SHA:

```bash
python -m ml.serving.score_pit_cli \
  --artifacts .local/ml-baselines \
  --trusted-manifest-sha256 YOUR_VERIFIED_SHA256 \
  --ledger .local/transaction-ledger.sqlite3 \
  --transaction-id YOUR_ACCEPTED_SYNTHETIC_TRANSACTION_ID \
  --persist-research-score
```

The integration CI job uses disposable Kafka + Confluent Schema Registry + Neo4j to ingest an Avro record, verify its graph edges, score the actual saved point-in-time snapshot against a separately trained synthetic model and assert replay stability. No paid AWS resources are provisioned. A raw manifest without an independent pin is rejected.

## Explicit constraints and next gates

- `pit-v1` historical context is a local SQLite implementation, not a distributed or production-grade feature store. The trained model uses GBP-only examples, simulated labels and a deliberately artificial latent fraud pattern.
- Even in the synthetic holdout, the previously chosen validation 5% FPR operating threshold did not meet 5% test FPR (XGBoost test FPR was 9.375%). **Do not use thresholds for automatic approval/decline.**
- Model-score numerical determinism is tested on this environment, but cross-platform library upgrades still need a pinned, audited build. The current requirements use version ranges; a dependency lockfile is outstanding.
- The existing `ml/serving/api.py` has different feature names, unvalidated model artifacts and heuristic descriptions. This CLI **does not certify** that API, deploy the new model there, or make heuristic explanations into SHAP.
- The SQLite research-score table is a local idempotency demonstration, not a compliant immutable audit store with role-based access, tamper protection or retention guarantees. It is not an analyst decision.
- No licensed external fraud dataset, entity-disjoint cold-start evaluation, calibrated output, SHAP result, case-management UI, full authentication, production load tests or cloud deployment has been proven.
- **Next priority:** genuine SHAP attribution calculated from this same verified model and feature vector; distinguish correlation from causation. Then an authenticated analyst-case action with immutable audit trail, and ultimately a reproducible synthetic source-to-case golden path.
