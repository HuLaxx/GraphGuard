# GraphGuard synthetic research model card — pit-v1 (NOT production)

**Model state:** experimental local research baseline, synthetic dataset only. **Not approved to determine fraud, deny payments, accuse customers, or serve real financial data.** This card covers the deterministic baseline evaluated in [CI 43611311872](https://github.com/HuLaxx/GraphGuard/actions/runs/43611311872), not an operational bank model. The generated model is loaded with an independently pinned artifact SHA-256 in [PR #7](https://github.com/HuLaxx/GraphGuard/pull/7).

## Intended use and explicit exclusions

**Intended:** demonstrate the engineering evidence chain from a first-observed synthetic ledger transaction through point-in-time features, a trained probability, model-derived SHAP and a human-only investigation workflow. Researchers can compare baselines and reproduce errors/latency locally.

**Not intended:** genuine fraud prediction; customer scoring, financial decisioning, payment approval/denial, debt/credit/lending eligibility, law-enforcement referral, regulatory audit, identity verification, discrimination/fairness assessment or large-scale deployment. SHAP is a model attribution, **not a causal explanation or proof of wrongdoing**. Review-close events are administrative case states, not fraud labels.

## Data provenance and feature contract

| Field | Grounded description |
|---|---|
| Origin | In-repo `synthetic-ml-v1` generator, seed 42, 720 transaction events, simulated positive labels and GBP currency |
| Split | Chronological train 65%, validation 15%, test 20%, with all source/ledger snapshots generated at first receipt |
| Holdout | 144 test records, 16 simulated positive labels |
| Features | 11 historical `pit-v1` user/device/merchant aggregates plus accepted current amount, input version `pit-v1+current-amount-v1` |
| Exclusions | Synthetic outcome, reviewer decisions, transaction/user/device IDs, IP, card fragments, future observations and source rowid |
| Leakage prevention | First-known/event-time cutoffs; train-only logistic scaling/class weights; validation-only model selection and thresholding |
| Limitations | Repeat users/devices overlap between splits, a narrow synthetic generator and a *known zero-new-user cold-start blind spot*; no independent licensed data |

Training/evaluation contract: [SYNTHETIC_BASELINES.md](SYNTHETIC_BASELINES.md). Dataset SHA-256 (seed-42 artifact):

`100b3ef3ae97ef7ea0d040de0bdbe31a6109cfe39f958d66eb3aeec57f0d3306`.

## Algorithms and measured held-out results

The experiment trains standardized, class-balanced **logistic regression** and weighted **XGBoost** with fixed parameters. It selects the model using **validation** PR-AUC, not test metrics; XGBoost was selected. An operating threshold was chosen to keep the validation-negative FPR at or below 5%, but this guarantee did **not** hold on untouched test data.

| Synthetic chronological holdout | Logistic regression | XGBoost |
|---|---:|---:|
| PR-AUC / average precision | 0.6887 | 0.7650 |
| ROC-AUC | 0.9072 | 0.9409 |
| Precision@25 | 0.52 | 0.52 |
| Recall at validation-selected threshold | 0.7500 | 0.8125 |
| **Realized test FPR** | **6.25%** | **9.375%** |
| Brier score | 0.0824 | 0.0695 |
| Ten-bin ECE | 0.1120 | 0.0630 |

These figures are **only** for synthetic labels and a fixed generator, seed, split and dependency set. A better PR-AUC on the synthetic task does not establish operational superiority, accuracy on real bank data, demographic fairness, statistical significance or calibration.

**Model artifacts SHA-256:** logistic `35acf88762b6f54701f1d2453876b74b3fb9fca39b4dfa3d09d097d11235aece`; XGBoost `87e40983a9294b60b3441c41f7c3c79ea1d0f7461d032cb6f429f1129a43a20e`. These are artifact-integrity references, **not cryptographic attestation of the developer or production model approval**.

## Validation-only post-calibration / drift research

[P2_CALIBRATION_DRIFT.md](P2_CALIBRATION_DRIFT.md) describes an *offline* Platt-scaling experiment: calibration fitted on the held-out validation period, original untouched chronological test evaluated separately, 150 moving-block descriptive bootstrap resamples, and PSI for the 12 features and model score. **Validation-period ECE is optimistic because it is in-sample calibration; PSI is not model concept drift or fairness proof.** This model card does not claim live monitoring, deployed calibrated inference, automatic retraining, safe production thresholding or validated rollback.

## Explainability and human review

The local [verified SHAP implementation](VERIFIED_SHAP.md) uses XGBoost native non-approximate TreeSHAP or exact linear Shapley attributions. Contributions are **signed raw log odds** and, with the baseline, reconstruct the same hash-verified model prediction. The local review API requires short-lived demo signer tokens for analyst/admin actions; the SQLite HMAC audit chain detects DB-only tampering without the separate signing key, but is **not** independently anchored or regulator-certified.

## Known harms, limitations and mitigations

- Synthetic scoring mistakes and uncalibrated outputs must **never** trigger automatic decisions. The observed XGBoost 9.375% test FPR exceeds the nominal 5% target and is a concrete warning.
- Historical proxies (shared devices, merchants, transaction volumes, amounts) may correlate with protected attributes or economic conditions. **No protected-group data, subgroup metrics, fairness evaluation or human impact assessment** is supplied; no claim of neutrality.
- A narrow simulator can reward synthetic patterns not present in real-world fraud. Same-user and shared-device overlap may inflate apparent generalization; unseen-user and unseen-merchant stress tests are not complete.
- Source hashes do not protect against an attacker holding all local signing keys and DB permissions. No enterprise identity, data retention policy, incident alerting, encryption-at-rest audit, independent log anchoring or multi-tenant isolation is demonstrated.
- The legacy GAT, RAG and old hosted scoring API are not approved or interchangeable with this `pit-v1` trained baseline.

## Reproduce, ownership and sign-off gates

```bash
python -m pip install -r requirements-ml-ci.txt
python -m pytest tests/unit/test_pit_baselines.py -v
python -m ml.training.pit_baselines --count 720 --seed 42 --output-dir .local/ml-baselines
```

Compare the generated `manifest.json` hashes/metrics with the trusted CI output. Do not blindly trust a manifest hash computed from an untrusted model directory. No real bank data or paid cloud services are required.

**Not signed off:** an independent licensed dataset, time-and-entity-disjoint external validation, calibration held-out over multiple real periods, subgroup impact/fairness and privacy testing, documented accepted FPR threshold, enterprise human-review access, trained model promotion/rollback, production monitoring, cloud cost authorization and independent security/model reviews. Until these exist, the only authorized status is **synthetic-only research/demo**.

**Evidence register:** [EVIDENCE_REGISTER.md](EVIDENCE_REGISTER.md) · [Progress scorecard](PROGRESS_SCORECARD.md) · [Source-to-browser candidate](P3_UNIFIED_BROKER_CHROMIUM.md).
