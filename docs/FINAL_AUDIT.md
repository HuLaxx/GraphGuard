# GraphGuard - Evidence Snapshot

This document is an evidence-first inventory of what exists in the repo. It does **not** claim that components are fully wired or production-ready.

## Code present (selected)

### Data engineering
- Kafka ingestion: `data-eng/producers/transaction_ingester.py`
- Kafka -> Neo4j consumer: `data-eng/consumers/graph_builder.py`
- Flink CEP patterns: `data-eng/flink/fraud_patterns.py`
- Spark features: `data-eng/spark/feature_engineering.py`
- Feast repo: `data-eng/feast/feature_repo/`
- Airflow DAG: `data-eng/airflow/dags/daily_feature_pipeline.py`
- Data quality checks: `data-eng/great_expectations/`

### ML training and explainability
- XGBoost baseline: `ml/training/baseline_xgboost.py`
- GAT model: `ml/training/gat_model.py`
- Ensemble: `ml/training/ensemble_model.py`
- SHAP analysis: `ml/explainability/shap_analysis.py`

### Serving and API
- FastAPI service: `ml/serving/api.py`
- GraphQL schema + resolvers: `backend/graphql/`
- RAG endpoints + indexing: `ml/serving/rag/`
- Prometheus metrics export: `ml/monitoring/performance_monitoring.py`

### Frontend
- Next.js app: `frontend/src/app/`
- D3 network graph: `frontend/src/components/dashboard/network-graph.tsx`
- SHAP chart: `frontend/src/components/dashboard/shap-chart.tsx`

### Infrastructure
- Local stack: `docker-compose.yml`
- Prometheus config: `infrastructure/prometheus/`
- Neo4j index scripts: `infrastructure/neo4j/`
- Terraform template: `infrastructure/terraform/main.tf`

## Verified execution evidence
- Python tests: `docs/evidence/python-tests-*.txt`
- Python coverage (RAG): `docs/evidence/python-coverage-*.txt` and `docs/evidence/coverage/rag/`
- Frontend tests (Vitest): `docs/evidence/frontend-tests-*.txt` and `docs/evidence/coverage/frontend/`
- CI config: `.github/workflows/ci.yml`
- Metrics export proof: `docs/evidence/metrics-*.txt`
- Docker Compose proof: `docs/evidence/docker-compose-ps-*.txt`
- API smoke run: `docs/evidence/api-health-*.txt`, `docs/evidence/api-score-*.txt`, `docs/evidence/api-metrics-*.txt`

## Known placeholders / partials
- GAT scoring in the API is stubbed (currently `gat_score = None`).
- Terraform is a template and has not been applied in this repo.

If you add verified outputs (benchmarks, load tests, screenshots), place them under `docs/evidence/` and link them here.
