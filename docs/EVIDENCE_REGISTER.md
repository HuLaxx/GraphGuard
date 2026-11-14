## P0 security and full CI verification — 12 November 2026

- **Current reviewed commit:** `3d686625013a59c2a6b7b07743cbd7c11a9e71d4`.
- **PASS** [GitHub Actions 43263873047](https://github.com/HuLaxx/GraphGuard/actions/runs/43263873047): frontend ESLint/TypeScript/Next production build, Python focused tests, frontend tests, existing MLflow Docker image build, and blocking high/critical Trivy dependency security scan.
- Dependency lockfile upgraded Next.js to **16.4.6**, lodash to **4.18.1** and source-map-js to **1.2.2**; the scan passed after these changes.
- This does not prove a GraphGuard API image, graph-to-model scoring golden path, production fraud accuracy or AWS deployment. Do not merge based on green narrow checks alone.

# GraphGuard — Engineering Evidence Register

Updated: 2026-11-12. Status labels refer to **observed evidence**, not intended architecture.

## Verification rules
- **Verified**: reproducible execution artifact with commands, commit, date and expected assertions.
- **Implemented, unverified**: source/config exists, but no current end-to-end test confirms behaviour.
- **Mock / stub**: explicitly simulated, hard-coded, placeholder or example behaviour.
- **Planned**: design, template or proposal only.

| Capability | Current status | Evidence | Next acceptance gate |
|---|---|---|---|
| Transaction event producer and Avro contract | Implemented, unverified | [Producer](../data-eng/producers/transaction_ingester.py), [schema](../data-eng/schemas/transaction_event.avsc) | Seed an event; validate schema, duplicate and replay cases |
| Kafka consumer to Neo4j | Implemented, unverified | [Graph builder](../data-eng/consumers/graph_builder.py) | Prove idempotent graph upsert with integration test |
| Feature engineering and data quality | Implemented, unverified | [Spark folder](../data-eng/spark/), [quality checks](../data-eng/great_expectations/) | Reproducible event-time windows and failure fixtures |
| XGBoost scoring and explainability | Implemented, unverified | [Training](../ml/training/train_xgboost_rigorous.py), [API](../ml/serving/api.py), [SHAP](../ml/explainability/shap_analysis.py) | Reproduce dataset provenance, time split and baseline metrics |
| GAT scoring | Stub / experimental | [Source audit](FINAL_AUDIT.md), [model](../ml/training/gat_model.py) | Replace stub and benchmark fairly, or exclude from supported claims |
| Hosted investigation UI | Mock / integration unverified | [Case page](../frontend/src/app/cases/page.tsx), [README](../README.md) | Seed event visible through real API, graph and case audit trail |
| Terraform / AWS | Planned; not deployed | [Terraform](../infrastructure/terraform/main.tf), [README](../README.md) | Security review, cost estimate, explicit approval, deployed proof |
| Python / frontend / lint CI | **Failed** on inspected main run | [GitHub Actions, 2026-11-06](https://github.com/HuLaxx/GraphGuard/actions/runs/42284437023) | Make all jobs pass on current head and record exact run |
| Historical Python tests | Dated result, not current CI | [Saved evidence](evidence/) | Re-run on current commit; publish commands and output |

## New PR verification (2026-11-12)

- [PR #1 check run 43199703064](https://github.com/HuLaxx/GraphGuard/actions/runs/43199703064): **3/3 focused Python RAG tests passed** and **4/4 frontend tests passed**.
- The same run's global frontend lint job **failed**. The first inspected lint log reports **69 errors and 14 warnings** across legacy frontend files. This is not a green PR or a full backend integration test.
- Root cause of the earlier Python test collection failure was eager import of the serving API from `ml/serving/__init__.py`, which imported `structlog` absent from the lightweight CI environment. The import is now lazy; `httpx` is explicitly declared for the RAG modules.

## P0 workflow finding
The inspected workflow invoked `pnpm install --frozen-lockfile` and `pnpm --filter ...`, but the repository declares npm and carries `frontend/package-lock.json`, with **no root pnpm lockfile**. That is a reproducible configuration mismatch, independent of the unknown cause of the Python test failure. The frontend also used `next lint` with Next.js 16. The linked failed run establishes the job outcomes; historical job logs could not be retrieved during this audit, so no further root cause is asserted.

## Required golden-path proof
1. Produce a deterministic, versioned transaction, including a duplicate and an invalid event.
2. Persist validated source data, route invalid records to quarantine/DLQ and upsert the graph idempotently.
3. Compute past-only features; score with a reproducible trained baseline and verified model artifact.
4. Display a correctly labelled explanation and create a human-reviewable case with a durable audit event.
5. Test disconnected infrastructure, retries, data leakage and UI mock boundaries.

## Current P0 release gate (2026-11-12)

- **PASS**: [Workflow 43253878251](https://github.com/HuLaxx/GraphGuard/actions/runs/43253878251), commit `5898540332e0d1d4abccd7b386960b85a211bfd8`, matches current draft PR head at time of verification.
- Frontend ESLint and TypeScript checks passed; focused Python RAG tests passed; frontend tests passed; the **existing MLflow image** built successfully.
- **Not claimed:** an API Docker image, a seeded Kafka->Neo4j->trained-model->case end-to-end test, GAT readiness, AWS infrastructure, or a hosted production fraud API. The image built was MLflow, not the missing API Dockerfile.

## Verification log
- 2026-11-12: examined repository tree, README, selected source paths and GitHub Actions statuses through the connected GitHub API.
- 2026-11-12: **No fresh test execution or AWS deployment was performed** in this audit environment. This document is not a green CI badge.
- Attach future PR runs, dataset hashes, command outputs and measurement artifacts below before upgrading a status to Verified.

## P1 at-least-once transaction recovery — 13 November 2026

- [Draft PR #2](https://github.com/HuLaxx/GraphGuard/pull/2), stacked on existing P0 PR #1. All changes are review-branch only; no production operations.
- [GitHub Actions 43427933012](https://github.com/HuLaxx/GraphGuard/actions/runs/43427933012), source SHA `d838dadb3841c7cfd21604ba3a32776b0b23de11`, verified the **14 focused Python tests passed**, including eleven new mock-client recovery cases; the frontend lint/test and high/critical security-scan jobs also passed. The MLflow image build was pending at this evidence-register update; check its final result before marking all jobs green.
- Graph builder now waits for Neo4j query result consumption before synchronously committing Kafka offsets. Failed graph writes or offset commits propagate and leave messages replayable instead of sending valid transactions to DLQ and committing them.
- The DLQ path requires a delivery callback acknowledgment before committing the original invalid message; a DLQ outage must not advance the source offset. Numeric and contract metadata are checked before buffering.
- Avro/schema registry failure now preserves the original offset instead of treating undecodable bytes as poisoned JSON. Synthetic JSON fixture mode is opt-in with `GRAPHGUARD_JSON_FIXTURE_MODE=true`.
- **Boundary:** tests run the real GraphBuilder policy methods but stub Kafka, Neo4j, schema registry and structured logging clients. They are **not** broker-backed integration or verified recovery under process restarts, rebalances and partial graph commits. One Neo4j `MERGE` batch is idempotent by node/edge identity but ON MATCH fields can be overwritten by conflicting duplicate IDs; transaction conflict control remains to be built.
- **Not verified:** full graph scoring/ML/SHAP, auditable investigator case, dataset licensing and leakage checks, complete auth hardening, a production Docker API image or AWS deployment. Provisioned cloud resources: none.

## P1 local durable ingestion candidate — 14 November 2026 (unverified pending CI)

- Review branch: `feature/graphguard-durable-ingestion-2026-11-14`, stacked on [PR #2](https://github.com/HuLaxx/GraphGuard/pull/2); NOT merged or deployed.
- Added `data-eng/consumers/transaction_ledger.py`: SQLite/WAL with full sync, transaction-ID uniqueness, canonical content SHA-256, immutable first accepted normalized source payload, partition/offset provenance and an append-only conflicting-ID inbox. Identical retries project again to repair a crash after source write; conflicting versions never replace the first ledger record.
- The source ledger deliberately does not persist raw IP addresses or card fragments. **Only use explicitly synthetic fixtures:** this local file is not an access-controlled production system or a substitute for governed data retention.
- GraphBuilder writes normalized source before graph projection. The graph uses unique ID constraints and a hash gate; count assertions execute inside a Neo4j write transaction before Kafka offset commit. Existing graph nodes without hashes require reconciliation instead of silent overwrite.
- Added `tests/unit/test_transaction_ledger.py` and expanded `tests/unit/test_graph_builder_delivery.py` for restart, duplicate/conflict, disk failure, ordering and graph hash mismatch. Results are not yet independently observed on this new branch.
- Added `docker-compose.ingestion.yml` and `tests/integration/test_ingest_kafka_neo4j.py` (opt-in), with disposable local Kafka and Neo4j; tests publish JSON fixtures on a real broker then query actual graph state, including a restart replay. This is **not** Avro+Schema Registry or a complete source-to-case journey.
- CI now includes the new unit tests and a separate Docker-backed integration job. Verify actual green run and link it before marking this milestone done.
- No AWS infrastructure, paid services, deployment, ML accuracy or analyst workflow is claimed.

### Reproduction for reviewers (synthetic fixtures only)

```bash
python -m pip install -r requirements-ci.txt -r requirements-ingestion-ci.txt
docker compose -f docker-compose.ingestion.yml up -d --wait
GRAPHGUARD_INGESTION_INTEGRATION=1 pytest tests/integration/test_ingest_kafka_neo4j.py -v
docker compose -f docker-compose.ingestion.yml down --remove-orphans
```

Known limitations: SQLite is a single-node local ledger; no transaction spanning SQLite, Kafka and Neo4j exists. Recovery relies on at-least-once Kafka replay and idempotent projection, not exactly-once delivery. Broker outages, partial commits, same-ID conflict behavior on existing legacy graph data, partition rebalancing, schema-registry outages and deployed auth require further verification.

## P1 verified acceptance snapshot — 13 November 2026 19:30 UTC

- [GitHub Actions CI 43492440036](https://github.com/HuLaxx/GraphGuard/actions/runs/43492440036), commit `dc892a0d8716775dba781663b93ece6485cb1306`.
- **PASS** Python focused suite: **23 tests** (3 RAG, existing and new recovery tests, local ledger tests) against this commit. [Python job](https://github.com/HuLaxx/GraphGuard/actions/runs/43492440036).
- **PASS** Docker-backed integration: **1 test** using a real Kafka broker plus Neo4j, with synthetic JSON fixtures, actual database assertions, a conflicting transaction-ID DLQ, first-record retention, duplicate projection and replay under a new consumer group.
- **PASS** frontend tests; **PASS** lint/typecheck/Next.js build; **PASS** high/critical dependency scan on that commit. Existing MLflow image build was queued when this snapshot was written.
- Subsequent branch changes normalize schema defaults and add additional privacy/identity unit tests. They are **not** counted as verified by the older run; check latest-head CI before merging.
- No Schema Registry/Avro wire-format integration, production cases, fraud accuracy claim, managed cloud resources or full golden path is demonstrated by this result.

## P1 — real Avro + Schema Registry acceptance (14 November 2026)

- **PASS, code SHA `c6ed9f400a71d3b7ffdd6fca80a2baf233576ccd`:** [CI run 43504349301](https://github.com/HuLaxx/GraphGuard/actions/runs/43504349301) completed with all six jobs successful. This evidence was observed from GitHub Actions jobs and logs.
- **27 focused Python unit tests passed.** The suite includes prior recovery policy, durable ledger, synthetic data privacy checks, and new fail-closed Avro framing tests. These unit methods use stubbed service clients.
- **4 real-service integration tests passed** on disposable Kafka, Neo4j and Confluent Schema Registry. Existing JSON-fixture ingestion remains separate from actual `TransactionProducer` Avro wire records. The Avro test verifies a registry subject/schema ID, persistent ledger, duplicate replay, immutable graph identity and conflicting same-ID DLQ.
- **Recovery:** a real consumer with an unreachable registry endpoint fails to decode without committing its source offset; a fresh consumer on the **same group** decodes and persists the record after the URL is restored. This simulates a network outage; it does not shut down the registry container.
- **PASS** frontend tests, frontend ESLint/typecheck/production build, high/critical Trivy manifest scan, and existing MLflow image build. A built MLflow image is not an API image.
- **Changed code:** `data-eng/producers/transaction_ingester.py`, `data-eng/consumers/graph_builder.py`, `tests/integration/test_avro_registry.py`, `tests/unit/test_graph_builder_delivery.py`, `requirements-ingestion-ci.txt`, `docker-compose.ingestion.yml`, `.github/workflows/ci.yml`; reproduction: [AVRO_INGESTION.md](AVRO_INGESTION.md).
- **Boundary:** schema evolution (backward/forward compatibility), arbitrary damaged wire data, rebalance and multi-partition offset behaviour, legacy graph migration, model scoring, analyst review, IAM/production auth and AWS remain unverified.
- These are PR-branch observations. The main branch has not been merged or certified. No cloud resources or paid services were provisioned.

## P1 — Immutable point-in-time features (14 November 2026)

- [Draft PR #5](https://github.com/HuLaxx/GraphGuard/pull/5), branch `feature/graphguard-point-in-time-features-2026-11-14`, stacked on PR #4. **No merge to main or production deployment.**
- `point_in_time_features.py` calculates `pit-v1` relationship features from accepted synthetic ledger data: user/merchant transactions, shared-device users, unique devices, and same-currency amount aggregates with 24h, 7d and 30d windows.
- **Temporal leakage control:** earlier event time (`h.event_time_ms < t.event_time_ms`) AND first-observed receipt ordering (`h.ledger_rowid < t.ledger_rowid` and receipt time `<=` target receipt). An event that arrives after a target is not retrospectively added, even when its event timestamp is older. Same-timestamp historical events are excluded.
- Versioned, immutable feature snapshots are saved in local SQLite with source payload hash, feature JSON hash, cutoff event/receipt times and feature version before Kafka offsets are acknowledged. Failed snapshot construction retains replayability. This is not a distributed exactly-once guarantee.
- [CI 43584978727](https://github.com/HuLaxx/GraphGuard/actions/runs/43584978727), source code SHA `bc1476026d1c7ddc0f123ccc5e7bc3da016f02b2`: **34 focused Python tests passed** (inspected job logs). Frontend, lint/typecheck/build, dependency scan and existing MLflow image build also passed; real-service integration was running at evidence-write time.
- [CI 43584904390](https://github.com/HuLaxx/GraphGuard/actions/runs/43584904390), source SHA `19e7750f03cdd039e0f5780c6ff95d872805b30c`: **5 integration tests passed with live Docker Kafka, Neo4j and Schema Registry**, including one new real Avro source → ledger → point-in-time feature snapshot acceptance and unchanged target snapshot after a late-arriving event. All 6 CI jobs passed on this source commit (the dedicated temporal Python test suite was added to CI on a subsequent commit).
- Tests also cover future-event ingestion order, equal event times, inclusive window boundaries, currency separation, restarts/replays, conflicting source identity, invalid ledger payloads and feature-write failures without Kafka offset commits.
- **Limitations:** no trained model uses these features yet; no Neo4j GDS computation, production data, distributed feature store, runtime benchmarks, genuine multi-consumer rebalance or historical entity-resolution governance. See [POINT_IN_TIME_FEATURES.md](POINT_IN_TIME_FEATURES.md).

## P1/P2 — Measured synthetic logistic/XGBoost baselines (14 November 2026)

- [Draft PR #6](https://github.com/HuLaxx/GraphGuard/pull/6), stacked on #5. Source commit `462e7c682bedd2595f672ef09f21d8333f06a114`, [**CI 43611311872**](https://github.com/HuLaxx/GraphGuard/actions/runs/43611311872): **all 7 jobs passed** (frontend lint/build, frontend tests, focused Python, high/critical security scan, real Kafka/Neo4j/Schema Registry integration, existing MLflow image build and new synthetic ML baseline job).
- The new ML job reports **6/6 targeted leakage/reproducibility tests passed** and actually trains both logistic-regression and XGBoost models using deterministic seed-42, **720 synthetic events** from the `pit-v1` ledger feature store. The earlier focused Python suite and five real-service Kafka/Neo4j tests remain separate; this is not a deployed scorer.
- Dataset SHA-256: `100b3ef3ae97ef7ea0d040de0bdbe31a6109cfe39f958d66eb3aeec57f0d3306`; model JSON SHA-256s: logistic `35acf88762b6f54701f1d2453876b74b3fb9fca39b4dfa3d09d097d11235aece`, XGBoost `87e40983a9294b60b3441c41f7c3c79ea1d0f7461d032cb6f429f1129a43a20e`. The workflow uploaded `manifest.json`, synthetic dataset and both native/JSON model artifacts under `graphguard-pit-ml-synthetic-baselines` (14-day retention).
- Strict chronological split: 65% train, 15% validation (**108 events, 13 synthetic positives**), 20% test (**144 events, 16 synthetic positives**). Repeated entity identities are audited and excluded from input columns; this is not entity-disjoint validation. Labels are simulated and never stored in the transaction source/feature store.
- **Validation PR-AUC:** logistic `0.8328`, XGBoost `0.8786`; **selected XGBoost using validation ONLY**. **Held-out synthetic test PR-AUC:** logistic `0.6887`, XGBoost `0.7650`; **test ROC-AUC:** `0.9072` and `0.9409`. **Test precision@25:** `0.52` for both; **recall at validation-selected threshold:** `0.75` and `0.8125`; **Brier:** `0.0824` and `0.0695`.
- **Critical operational limitation:** threshold chosen to cap *validation* false-positive rate at 5% did **not** achieve 5% on the held-out test. Measured test FPR was **6.25%** (logistic) and **9.375%** (XGBoost). Do not advertise or automate decisions using a 5% guaranteed operating point.
- Frozen feature contract: `pit-v1+current-amount-v1` (11 past-only graph-context features plus known current amount). Fixed hyperparameters; train-only scaler/weights; test labels do not affect training or model selection. Manifest records installed dependency versions and split entity-overlap counts. Script uses safe JSON model records and verifies native XGBoost reload rather than trusting a pickle.
- **No external fraud dataset/licence, real customer outcomes, calibrated/fairness guarantee, model registry/MLflow experiment, SHAP on a scored instance, deployed API, authenticated analyst case, or AWS provisioning is verified.** Results are valid **only for this synthetic generator**. See [SYNTHETIC_BASELINES.md](SYNTHETIC_BASELINES.md).
