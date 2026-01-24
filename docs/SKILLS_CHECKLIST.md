# GraphGuard - Skills Map (Evidence-based)

Purpose: document skills demonstrated by code present in this repo. No performance or scale claims are made here.

## ML Engineer
Evidence (code present):
- XGBoost training pipeline: `ml/training/baseline_xgboost.py`
- GAT model training (PyTorch): `ml/training/gat_model.py`
- Ensemble model: `ml/training/ensemble_model.py`
- SHAP analysis utilities: `ml/explainability/shap_analysis.py`
- MLflow tracking artifacts: `mlruns/`

Partial / template:
- Production-grade model registry and promotion workflows are templates (see `ml/pipelines/`).

Tech used in repo:
- XGBoost, PyTorch, SHAP, MLflow, pandas/numpy

## Data Engineer
Evidence (code present):
- Kafka ingestion and consumer: `data-eng/producers/`, `data-eng/consumers/`
- Flink CEP patterns: `data-eng/flink/fraud_patterns.py`
- Spark feature engineering: `data-eng/spark/feature_engineering.py`
- Feast feature repo: `data-eng/feast/feature_repo/`
- Airflow DAG: `data-eng/airflow/dags/daily_feature_pipeline.py`
- Data quality checks: `data-eng/great_expectations/`

Partial / template:
- End-to-end pipeline orchestration is not wired in CI.

Tech used in repo:
- Kafka, Flink, Spark, Feast, Airflow, Great Expectations

## Backend Engineer
Evidence (code present):
- FastAPI service: `ml/serving/api.py`
- GraphQL schema + resolvers: `backend/graphql/`
- API key auth + CORS config: `ml/serving/api.py`
- Redis feature cache: `ml/serving/feature_cache.py`
- Optional rate limiting middleware: `ml/serving/rate_limiter.py`
- Prometheus metrics export: `ml/monitoring/performance_monitoring.py`

Partial / template:
- GAT scoring in API is stubbed (see `ml/serving/api.py`).

Tech used in repo:
- FastAPI, Strawberry GraphQL, Pydantic, Redis, Neo4j

## MLOps / Platform Engineer
Evidence (code present):
- Local infra stack: `docker-compose.yml`
- Prometheus config: `infrastructure/prometheus/`
- Terraform template: `infrastructure/terraform/main.tf`
- CI workflow: `.github/workflows/ci.yml`
- RAG indexing + vector storage: `ml/serving/rag/`

Partial / template:
- No Kubernetes/Helm manifests included.
- Terraform has not been applied or validated.

Tech used in repo:
- Docker Compose, Prometheus, Terraform (template), GitHub Actions, pgvector (via Postgres)

## Full-Stack Engineer
Evidence (code present):
- Next.js UI: `frontend/src/app/`
- D3 network visualization: `frontend/src/components/dashboard/network-graph.tsx`
- SHAP chart: `frontend/src/components/dashboard/shap-chart.tsx`
- RAG assistant UI: `frontend/src/components/assistant/rag-assistant.tsx`
- GraphQL client setup: `frontend/src/lib/apollo-client.ts`

Tech used in repo:
- Next.js, React, TypeScript, D3, Tailwind CSS, Radix UI, Apollo Client, React Query, Zod
