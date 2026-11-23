# GraphGuard P1 — Model-derived SHAP explanations, synthetic-only

**Status:** local research attribution for the exact hash-pinned model and immutable `pit-v1` synthetic transaction snapshot. **Not** evidence of actual fraud, a causal explanation, a production scoring API, a calibrated risk estimate or an authenticated human decision.

## What is actually computed?

1. Use the `VerifiedSyntheticScorer` introduced in [PR #7](https://github.com/HuLaxx/GraphGuard/pull/7). It must receive an **independently trusted SHA-256 of the model manifest**. The scorer verifies model bytes, feature order, source payload hash, point-in-time feature-snapshot hash, event and first-knowledge cutoffs, synthetic-only scope and GBP-only input.
2. Re-read the exact source and snapshot, recheck their hashes against the verified score and reconstruct the *same ordered 12 input columns* (`pit-v1` historical graph features plus accepted current amount). No user ID, outcome, fraud label, IP or card fragment enters the explanation model.
3. **XGBoost:** call its real native `Booster.predict(DMatrix, pred_contribs=True, approx_contribs=False)` TreeSHAP algorithm. This is **exact native tree-path-dependent TreeSHAP** for the trained model; no randomly generated importance, heuristic thresholds, sampled fake SHAP, or fitted external explainer. Its reported baseline is the trained booster path-dependent log-odds baseline, **not a causal or population reference**.
4. **Logistic regression:** use the exact additive Shapley decomposition for the standardized linear logit model relative to the saved *training feature means*: `(value - training_mean) / training_scale × coefficient`. The frozen intercept is the baseline log-odds. This is a **training-mean additive reference**; correlated-feature/conditional attribution is *not* inferred.
5. Both paths operate on **log odds**, not percentage-point probability changes. `baseline_log_odds + sum(feature_SHAP_log_odds)` reconstructs the raw prediction; stable sigmoid reconstruction must match the independently verified model probability to within `2e-5`. An incorrect shape, nonfinite value or inconsistent reconstruction fails closed.
6. Return ranked top-K **signed** numeric attributions (absolute-value descending, stable feature-name tie-break), all feature contributions, model/manifest/source/feature SHA-256 references, feature-input/explainer version, reconstruction error and a conspicuous non-causality warning.
7. Optional local SQLite research persistence requires a matching **already verified saved score**. The writer recomputes the entire explanation with the pinned scorer before the first INSERT. Exact Kafka replay is idempotent and cannot overwrite a previously different explanation for the same `(transaction_id, manifest, explainer_version)`.

## Reproduce on Python 3.11 (no paid tools or cloud)

```bash
python -m pip install -r requirements-ml-ci.txt
python -m pytest tests/unit/test_verified_shap.py -v
python -m ml.training.pit_baselines --count 720 --seed 42 --output-dir .local/ml-baselines
sha256sum .local/ml-baselines/manifest.json
```

Once a **synthetic** transaction has been ingested into a local SQLite ledger using the Avro acceptance pipeline (see `docs/AVRO_INGESTION.md`), copy the *verified* manifest pin from your independently trusted CI/build source. Do not calculate a pin from an untrusted artifact and call that authentication.

```bash
python -m ml.explainability.explain_pit_cli \
  --ledger .local/transaction-ledger.sqlite3 \
  --artifacts .local/ml-baselines \
  --trusted-manifest-sha256 YOUR_TRUSTED_64_CHAR_SHA256 \
  --transaction-id YOUR_ACCEPTED_SYNTHETIC_ID \
  --top-k 5 \
  --persist-research-artifacts
```

The `--persist-research-artifacts` flag is optional and writes a locally revalidated research **score + explanation**, not an operational case, accusation or reviewer decision.

### CI acceptance

The ML job runs real model training/roundtrip tests, exact XGBoost TreeSHAP vs native booster checks, logistic additive reconstruction, signed contributions, stable hashes/replay, feature-order/manifest tampering and rejection of forged explanations. The integration job brings up **actual disposable Kafka, Schema Registry and Neo4j**, sends a synthetic registered Avro event, persists `pit-v1`, loads the trusted trained model, computes genuine SHAP and asserts repeatability under Kafka replay.

Accept the work only when the **same current-head commit** has a green CI run; quote precise job counts/log links in the evidence register rather than assuming passing tests.

## Hard limitations

- Shapley contributions are **model attributions, not causal evidence or real-fraud proof**. A large positive log-odds contribution is not a human judgment or policy threshold.
- The previous synthetic XGBoost validation FPR target of 5% produced **9.375% test FPR**. The model is not safe for automated declines, and these explanations do not change that.
- TreeSHAP uses the booster tree-path-dependent background, not an external independent baseline; correlated features may redistribute credit. Logistic values use a training-mean baseline without dependency modeling.
- This is a local deterministic synthetic proof: no production data, third-party dataset validation, SHAP fairness guarantee, runtime performance SLA, full dependency lockfile, live API integration, or secured model registry.
- A hash is **integrity evidence only**. A separately supplied pin is the trust boundary; an attacker with unrestricted local filesystem or SQLite write privileges can rewrite the research data. The local append-only convention is not a cryptographically tamper-proof compliance ledger.
- No automated approve/decline, case state transition, RAG evidence, reviewer identity, RBAC, authenticated UI or retention controls have yet been verified.

**Next P1 milestone:** authenticated synthetic human-review case creation with traceable feature/model/explanation hashes, append-only reviewer decisions and a demonstrated end-to-end source → graph → features → model → SHAP → analyst case sequence.
