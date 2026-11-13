# GraphGuard — Engineering Release Checklist (evidence-gated)

**Updated:** 2026-11-14 | **Target:** defensible Applied ML / Graph Data Engineering / MLOps flagship | **Status:** DRAFT, NOT 10/10

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
- [ ] Compute past-only graph features with event-time windows, deterministic entity resolution and no future leakage.
- [ ] Train/load a real versioned model artifact and score the new transaction; prove exact model hash/version.
- [ ] Display a correctly labelled explanation (SHAP = attribution, **not causation**).
- [ ] Create an authenticated human-review case, record a decision and persist immutable audit history.
- [ ] Run one seeded command sequence proving source → graph → features → model → explanation → analyst case.

## P2 — Reproducible ML and model governance
- [ ] Record dataset licence, synthetic/public limitations, class balance, deidentification and schema.
- [ ] Logistic regression and XGBoost baselines with deterministic environment/seeds and chronological holdout.
- [ ] Test entity leakage, identity overlap, target leakage and feature availability at decision time.
- [ ] Report PR-AUC, recall at stated FPR, precision@K, calibration, review volume and uncertainty with scripts/artifacts.
- [ ] SHAP feature-attribution plots validated on actual scored instances; no causal or individual-accusation claims.
- [ ] Model registry/provenance, MLflow experiment tracking and audited promote/rollback.
- [ ] Drift, model health and human-review feedback loops with thresholds, false-positive monitoring and rollback test.
- [ ] Either implement and benchmark GAT fairly against strong tabular baselines **or remove operational GAT claims**.
- [ ] Bound RAG retrieval to real indexed documents with verifiable citations and prompt-injection tests.

## P3 — Security, reliability, cloud and costs
- [ ] Enforce reviewer/admin roles; minimise PII, mask identifiers and restrict case access/retention.
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
- **Current gate:** real Kafka, Schema Registry and Neo4j ingestion **verified for synthetic fixtures only** on [CI 43504349301](https://github.com/HuLaxx/GraphGuard/actions/runs/43504349301): 27 focused Python unit tests, 4 real-service integration tests, six passing jobs. Full graph → ML/SHAP → analyst-case integration is **not** verified.
- **Current draft PR:** [#4](https://github.com/HuLaxx/GraphGuard/pull/4), stacked on [#3](https://github.com/HuLaxx/GraphGuard/pull/3), [#2](https://github.com/HuLaxx/GraphGuard/pull/2), [#1](https://github.com/HuLaxx/GraphGuard/pull/1). The code commit `c6ed9f4` has all six checks green. Next highest-value work: deterministic, point-in-time graph features with chronological leakage/replay tests, followed by genuine model scoring. Keep all PRs draft until reviewed.
- **Never claim:** production bank fraud detection, fairness guarantees, live customers, GAT readiness or AWS deployment without exact evidence.
