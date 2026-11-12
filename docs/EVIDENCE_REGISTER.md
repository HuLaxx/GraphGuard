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
