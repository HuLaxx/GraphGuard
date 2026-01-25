# GraphGuard - Project Snapshot (Evidence-based)

Status: Portfolio build. Local demo is supported; cloud deployment is not fully wired in this repo.

## What exists in the repo
- Data engineering pipeline code (Kafka, Flink, Spark, Feast, Airflow, Great Expectations)
- ML training scripts (XGBoost, GAT, ensemble) and SHAP explainability utilities
- FastAPI scoring service with optional GraphQL and RAG endpoints
- Next.js dashboard with D3 network graph and SHAP chart components
- Local Docker Compose stack and Prometheus config

## Evidence artifacts
- Test and coverage logs are stored in `docs/evidence/`.
- See `docs/FINAL_AUDIT.md` for an evidence-first inventory.

## How to run locally
1) `cp .env.example .env`
2) `docker-compose up -d`
3) `python -m uvicorn ml.serving.api:app --reload --port 8000`
4) `cd frontend && npm install && npm run dev`

Notes:
- API requests require `API_KEY` via environment variables.
- `/metrics` is currently a placeholder endpoint.
- GAT scoring in the API path is stubbed.
