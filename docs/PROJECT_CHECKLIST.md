# GraphGuard - Implementation Inventory

Legend:
- [x] Code present in repo
- [~] Partial / placeholder implementation
- [ ] Not implemented in repo

## Infrastructure
- [x] Local Docker Compose stack (`docker-compose.yml`)
- [x] Prometheus config (`infrastructure/prometheus/`)
- [x] Neo4j indexes (`infrastructure/neo4j/`)
- [~] Terraform template (`infrastructure/terraform/main.tf`)
- [ ] Kubernetes / Helm manifests
- [ ] Container build scripts / Dockerfiles

## Data Engineering
- [x] Kafka producer (`data-eng/producers/transaction_ingester.py`)
- [x] Kafka -> Neo4j consumer (`data-eng/consumers/graph_builder.py`)
- [x] Flink CEP patterns (`data-eng/flink/fraud_patterns.py`)
- [x] Spark feature engineering (`data-eng/spark/feature_engineering.py`)
- [x] Feast feature repo (`data-eng/feast/feature_repo/`)
- [x] Airflow DAG (`data-eng/airflow/dags/daily_feature_pipeline.py`)
- [x] Great Expectations checks (`data-eng/great_expectations/`)

## ML / Data Science
- [x] XGBoost baseline (`ml/training/baseline_xgboost.py`)
- [x] GAT model training (`ml/training/gat_model.py`)
- [x] Ensemble model (`ml/training/ensemble_model.py`)
- [x] SHAP analysis (`ml/explainability/shap_analysis.py`)

## Serving / API
- [x] FastAPI scoring (`ml/serving/api.py`)
- [~] GAT scoring in API (stubbed in `ml/serving/api.py`)
- [x] Prometheus `/metrics` export (`ml/monitoring/performance_monitoring.py`)
- [x] GraphQL schema/resolvers (`backend/graphql/`)
- [x] RAG endpoints + indexer (`ml/serving/rag/`)

## Frontend
- [x] Next.js app (`frontend/src/app/`)
- [x] Dashboard components (`frontend/src/components/dashboard/`)
- [x] D3 network graph (`frontend/src/components/dashboard/network-graph.tsx`)
- [x] SHAP chart (`frontend/src/components/dashboard/shap-chart.tsx`)
- [x] RAG assistant UI (`frontend/src/components/assistant/rag-assistant.tsx`)

## Tests & Evidence
- [x] Python unit/integration tests (`tests/unit/`, `tests/integration/`)
- [x] k6 load test script (`tests/load/k6_load_test.js`) (not executed in CI)
- [x] Frontend unit tests (`frontend/src/lib/utils.test.ts`)
- [x] Evidence logs (`docs/evidence/`)

## How to verify
- Python: `pytest tests/unit/test_rag.py -v`
- Frontend: `cd frontend && pnpm test`
- Evidence artifacts: `docs/evidence/`
