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
