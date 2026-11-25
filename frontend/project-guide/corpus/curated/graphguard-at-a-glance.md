# GraphGuard at a glance

## What GraphGuard is

GraphGuard is Rahul Khanke's graph-based fraud investigation project. It shows how a suspicious transaction should become a reviewable investigation rather than an automatic fraud verdict: events are ingested, relationships between accounts, devices and merchants are projected into a graph, a model scores the transaction with explanations, and a human analyst reviews the case. All data is synthetic. Demo: https://graph-guard-frontend.vercel.app. Source: https://github.com/HuLaxx/GraphGuard.

## Tech stack

- Ingestion: Kafka with Avro and Confluent Schema Registry, a durable first-observed SQLite source ledger.
- Graph: Neo4j with Cypher for user, device and merchant relationships; point-in-time (leakage-safe) graph-context features.
- Machine learning: scikit-learn logistic regression and XGBoost trained on chronological splits, an MLflow-based release gate, hash-pinned (SHA-256) model and feature artifacts, native XGBoost TreeSHAP explanations, offline calibration and drift monitoring.
- Serving and review: Python FastAPI review API with signed short-lived reviewer and admin identities and a keyed local audit chain; a GraphQL demo API.
- Frontend: Next.js 16, React, TypeScript, Tailwind CSS, D3 network graph and SHAP charts, Vitest tests.
- Delivery: Docker Compose, GitHub Actions CI (including real Kafka/Avro/Schema Registry/Neo4j integration jobs, Chromium analyst/admin review tests, npm audit and a Trivy security scan), review-only Terraform for an opt-in AWS research sandbox.

## Model results (synthetic only)

On a deterministic synthetic chronological holdout (720 events, 144 test records, 16 simulated positives), XGBoost reached PR-AUC 0.7650 and ROC-AUC 0.9409, against 0.6887 and 0.9072 for logistic regression. Its realised test false-positive rate was 9.375%, above the 5% budget chosen on validation data, which the model card reports as a limitation. These are synthetic research numbers, not real-world fraud accuracy.

## What is verified and what is not

Verified in CI: Avro records through Kafka and Schema Registry into Neo4j, point-in-time features, a hash-pinned model, genuine native SHAP, signed local case review in real Chromium, and dependency security scans. The project scores itself 70/100 on an evidence-weighted release scorecard. Not claimed: production deployment, real or licensed fraud data, enterprise OIDC/MFA, independently anchored audit, production load testing, or provisioned cloud infrastructure. The hosted GraphQL demo is illustrative and is not the signed Python case service.
