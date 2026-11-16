# GraphGuard — Engineering Release Checklist (evidence-gated)

**Updated:** 2026-11-16 | **Target:** defensible Applied ML / Graph Data Engineering / MLOps flagship | **Status:** DRAFT, NOT 10/10

Mark [x] only when supported by a reproducible test on an identified commit. A green narrow CI suite does **not** prove broker-backed ingestion, fraud accuracy or production readiness. Link every supported release claim in [EVIDENCE_REGISTER.md](EVIDENCE_REGISTER.md). This system supports **human investigation** and must never present a score as proof of wrongdoing.

## P0 — Integrity, CI and provenance
- [x] Repaired npm/ESLint/test configuration and passed frontend, focused Python and security checks on P0 review branch. [PR #1](https://github.com/HuLaxx/GraphGuard/pull/1), [CI 43266229261](https://github.com/HuLaxx/GraphGuard/actions/runs/43266229261).
- [x] Verified MLflow **container build only**, not GraphGuard API container or MLOps end-to-end. [CI 43266229261](https://github.com/HuLaxx/GraphGuard/actions/runs/43266229261).
- [x] Added real vs mock vs planned capability inventory and explicit GAT-stub limitation. [EVIDENCE_REGISTER.md](EVIDENCE_REGISTER.md).
- [x] Tested GraphBuilder handling of transient Neo4j failure, offset commit, acknowledged DLQ and schema-decoder outage with simulated service clients. [PR #2](https://github.com/HuLaxx/GraphGuard/pull/2), [CI 43428457363](https://github.com/HuLaxx/GraphGuard/actions/runs/43428457363).
- [ ] Validate full dependency lockfiles, secrets, model files, provenance, licence and API Docker build.
- [ ] Expand real Kafka/Neo4j outage/rebalance/partial-commit drills (existing CI now includes live broker, registry, graph, duplicate, conflict and unreachable-registry recovery; not all failure modes).
- [ ] Review stacked PRs and merge only after approval; no main or production mutation without review.

## P1 — Real transaction → graph → investigation golden path
- [x] A failed Neo4j batch no longer silently DLQs valid transactions while committing offsets; mock-client tests support at-least-once retry policy. [PR #2](https://github.com/HuLaxx/GraphGuard/pull/2).
- [x] Malformed numeric amounts, identifiers, timestamps, currencies and schema outages have focused handling tests. [PR #2](https://github.com/HuLaxx/GraphGuard/pull/2).
- [x] Verify actual `TransactionProducer` v1 Avro wire records through real Schema Registry → Kafka → `GraphBuilder` → ledger → Neo4j, including duplicate/conflicting-ID replay. [PR #4](https://github.com/HuLaxx/GraphGuard/pull/4), [CI 43504349301](https://github.com/HuLaxx/GraphGuard/actions/runs/43504349301), code SHA `c6ed9f4`.
- [ ] Validate source timestamp and provenance end-to-end in the real Avro path.
- [x] Ran disposable Kafka/Neo4j JSON-fixture integration: real broker events, graph projection, same-ID conflict DLQ, duplicate and replay verification. [CI 43492440036](https://github.com/HuLaxx/GraphGuard/actions/runs/43492440036), commit `dc892a0`.
- [x] Verified local SQLite ledger persistence, topic/partition/offset provenance and replay after restart on commit `dc892a0` (23 Python tests plus real-broker integration). [CI 43492440036](https://github.com/HuLaxx/GraphGuard/actions/runs/43492440036).
- [x] Prove real Kafka → validated SQLite source ledger → Neo4j transaction and relationship edges in running integration tests using both JSON fixtures and Schema Registry-backed Avro. [CI 43504349301](https://github.com/HuLaxx/GraphGuard/actions/runs/43504349301).
- [x] Verified canonical SHA-256 / duplicate / conflicting-ID path with SQLite ledger and graph identity checks on synthetic fixtures, including real Kafka/Neo4j integration at `dc892a0`. Legacy-graph migration remains unverified. [CI 43492440036](https://github.com/HuLaxx/GraphGuard/actions/runs/43492440036).
- [ ] Verify duplicate delivery, restarts, broker outage, graph outage, poison event, DLQ failure and replay without silent loss.
- [x] Implemented and tested `pit-v1` historical graph-context aggregates from accepted ledger relationships, with strict event-time/receipt-order cutoffs, immutable snapshots, late arrivals, mixed currencies and replay. **Synthetic single-ledger scope only.** [PR #5](https://github.com/HuLaxx/GraphGuard/pull/5), [34 Python tests](https://github.com/HuLaxx/GraphGuard/actions/runs/43584978727), [5 real-service tests](https://github.com/HuLaxx/GraphGuard/actions/runs/43584904390). Cross-provider entity resolution still requires validation.
- [x] **Synthetic-only** real Avro → Kafka → Neo4j/ledger → `pit-v1` features → **hash-pinned trained model research score**, with untrusted-write hardening and replay. [PR #7](https://github.com/HuLaxx/GraphGuard/pull/7), [all 7 jobs green + 16 unit tests CI 43687400391](https://github.com/HuLaxx/GraphGuard/actions/runs/43687400391). **Hosted API, analyst case and production deployment remain unverified.**
- [x] **Verified genuine native TreeSHAP or analytic linear Shapley** for the same pinned, accepted synthetic model event, with all log-odds features rebuilding the verified score, hashes and replay-stable local research record. [PR #8](https://github.com/HuLaxx/GraphGuard/pull/8), [30 ML unit + 6 real-service tests, 7/7 jobs green CI 43711547865](https://github.com/HuLaxx/GraphGuard/actions/runs/43711547865). **This is CLI/numerical evidence; production UI and human case remain unverified.**
- [ ] Display attribution in an authenticated UI with a clear model-versus-causality disclaimer; numeric local CLI is complete, production UI is not.
- [x] **Signed local synthetic analyst demo**: exact source/feature/model/SHAP hashes anchor a review case; HMAC-signed short-lived analyst/admin tokens enforce review actions, admin-only closure; append-only SQLite events with hash-chain + HMAC and trigger protection; replay-safe, version-checked. [PR #9](https://github.com/HuLaxx/GraphGuard/pull/9), [37 focused + 6 real integration tests; 7/7 green jobs CI 43922849789](https://github.com/HuLaxx/GraphGuard/actions/runs/43922849789). **Not enterprise OIDC, externally anchored audit, production deployed auth or real customer decisions.**
- [x] Real-service deterministic synthetic acceptance test verifies **Avro → Kafka/Registry → Neo4j → `pit-v1` → trained model → SHAP → signed analyst case → admin decision → Kafka replay** in disposable services. [CI 43922849789](https://github.com/HuLaxx/GraphGuard/actions/runs/43922849789). [ ] A polished **single-command standalone demo launcher** that also starts and tears down Docker remains outstanding.

## P2 — Reproducible ML and model governance
- [x] Recorded in-repo synthetic-generator provenance, seed, class distribution, dataset hash, split dates, explicit feature schema and no external dataset licence. **External licensed real/public dataset evidence remains open.** [PR #6](https://github.com/HuLaxx/GraphGuard/pull/6), [CI 43611311872](https://github.com/HuLaxx/GraphGuard/actions/runs/43611311872).
- [x] Trained logistic regression and XGBoost on deterministic seed-42 `pit-v1` synthetic snapshots, strict chronological 65/15/20 holdout and train-only weights/scaling; saved versioned JSON artifacts with hashes. [CI 43611311872](https://github.com/HuLaxx/GraphGuard/actions/runs/43611311872).
- [ ] Source identity is excluded from an explicit feature allowlist; repeat-user/device overlap is **audited** and test-label-isolation assertions pass. Remaining: independent entity-disjoint cold-start and true feature-availability validation on public data. [PR #6](https://github.com/HuLaxx/GraphGuard/pull/6).
- [ ] Reported measured validation/test PR-AUC, ROC-AUC, precision@25, recall/realized FPR and Brier/ECE in downloadable synthetic manifest. **Remaining:** confidence intervals, calibration corrections and review volume/cost simulations. Test FPR exceeded the validation 5% budget (XGBoost 9.375%). [CI 43611311872](https://github.com/HuLaxx/GraphGuard/actions/runs/43611311872).
- [ ] Actual SHAP *numeric values* are now verified for hash-pinned real-service synthetic scored instances [PR #8](https://github.com/HuLaxx/GraphGuard/pull/8), [CI 43711547865](https://github.com/HuLaxx/GraphGuard/actions/runs/43711547865). **Outstanding:** published attribution plots, multiple-instance stability, correlated-feature sensitivity and analyst-facing interpretation (no causal or accusation claims).
- [ ] Model registry/provenance, MLflow experiment tracking and audited promote/rollback.
- [ ] Drift, model health and human-review feedback loops with thresholds, false-positive monitoring and rollback test.
- [ ] Either implement and benchmark GAT fairly against strong tabular baselines **or remove operational GAT claims**.
- [ ] Bound RAG retrieval to real indexed documents with verifiable citations and prompt-injection tests.

## P3 — Security, reliability, cloud and costs
- [ ] **Local signed reviewer/admin roles and minimized synthetic source records implemented** in [PR #9](https://github.com/HuLaxx/GraphGuard/pull/9), with HMAC-protected audit and explicit per-request authentication in the local service. **Still required for P3:** real OIDC/SSO/MFA, token revocation and key rotation, multi-user/data retention/access policies, independent audit anchoring, privacy threat model and production audit tests.
- [ ] Structured logs, tracing where useful, alert thresholds and broker/graph/model runbooks.
- [ ] Failure/recovery drills and load/latency measurements with reproducible scripts and datasets.
- [ ] Costed optional AWS S3/artifacts, EventBridge/Step Functions, on-demand training/serving, CloudWatch, IAM/OIDC and Secrets Manager.
- [ ] Explicit authorisation before paid AWS actions; document genuine provisioned-vs-template infrastructure and teardown.
- [ ] Evaluate local vs managed graph database with a transparent monthly cost comparison.

## P4 — Demo and UK job-market publication
- [ ] Case UI distinguishes mock, synthetic, measured and real integrations at every screen.
- [ ] README, architecture diagram, CI links, model card, reproducibility commands and security/ethical limitations agree with implementation.
- [ ] Link real model evaluation plots, exact dataset versions, screenshots, demo and benchmark artifacts.
- [ ] Publish a clear 5–8 minute ML/MLOps interview story: leakage, false positives, human decisions and recovery.
- [ ] Publish GraphGuard as lead ML/MLOps example **only when** real source-to-case golden path is independently reproducible.

## Release decision
- **Current gate:** synthetic source-to-**signed local human review decision** proven in code SHA `aac70762`, [CI 43922849789](https://github.com/HuLaxx/GraphGuard/actions/runs/43922849789): **7/7 green jobs, 37 focused Python/ML/review unit tests, 6 real-service integration tests**. No production auth, UI wiring, external dataset, compliance-grade audit or deployment; final docs-head CI must separately pass.
- **Current draft PR:** [#9](https://github.com/HuLaxx/GraphGuard/pull/9), stacked on [#8](https://github.com/HuLaxx/GraphGuard/pull/8) → [#7](https://github.com/HuLaxx/GraphGuard/pull/7) → [#6](https://github.com/HuLaxx/GraphGuard/pull/6) → [#5](https://github.com/HuLaxx/GraphGuard/pull/5) → [#4](https://github.com/HuLaxx/GraphGuard/pull/4) → [#3](https://github.com/HuLaxx/GraphGuard/pull/3) → [#2](https://github.com/HuLaxx/GraphGuard/pull/2) → [#1](https://github.com/HuLaxx/GraphGuard/pull/1). **Next:** local synthetic analyst UI wired to this exact signed API, SHAP plots and verifiable case timeline. Keep all drafts unmerged until review.
- **Never claim:** production bank fraud detection, fairness guarantees, live customers, GAT readiness or AWS deployment without exact evidence.
