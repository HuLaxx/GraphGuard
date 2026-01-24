<div align="center">
  <h1>GraphGuard</h1>
  <p>Real-time transaction network fraud detection with explainable Graph AI</p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.11%2B-blue" alt="Python" />
    <img src="https://img.shields.io/badge/FastAPI-009688" alt="FastAPI" />
    <img src="https://img.shields.io/badge/Next.js-16-black" alt="Next.js" />
    <img src="https://img.shields.io/badge/GraphQL-Strawberry-E10098" alt="GraphQL" />
    <img src="https://img.shields.io/badge/Docker-Compose-2496ED" alt="Docker" />
  </p>

  <p>
    <a href="#quick-start">Quick Start</a> | <a href="#features">Features</a> | <a href="#architecture">Architecture</a> | <a href="#api">API</a> | <a href="#testing">Testing</a>
  </p>
</div>

---

## Overview

GraphGuard is a portfolio-grade, evidence-first fraud detection platform. It combines classic ML (XGBoost) with graph analytics (Neo4j + GAT training) and a local-first RAG assistant. Heavy services run locally; the hosted demo is intentionally lightweight and uses free-tier services.

## Features

| Area | What it covers | Where it lives |
| --- | --- | --- |
| Real-time ingestion | Kafka producer/consumer flow and Flink CEP patterns | data-eng/ | 
| Graph intelligence | Neo4j graph build + algorithms | data-eng/neo4j/ |
| ML scoring | XGBoost scoring API + GAT training scripts | ml/serving/, ml/training/ |
| Explainability | SHAP explanations surfaced in the UI | ml/explainability/, frontend/ |
| RAG assistant | Local-first repo indexing + Q&A | ml/serving/rag/ |
| Observability | Prometheus metrics endpoint and dashboards | ml/monitoring/, infrastructure/ |

## Quick Start

### Prerequisites

- Docker Desktop
- Python 3.11+
- Node.js 18+ and pnpm

### 1) Start the local stack

```bash
cp .env.example .env

docker compose up -d
```

### 2) Run the API

```bash
python -m uvicorn ml.serving.api:app --host 127.0.0.1 --port 8000
```

### 3) Run the frontend

```bash
pnpm -C frontend dev -- --port 3000
```

If the API is not on port 8000, set this before running the frontend:

```bash
set NEXT_PUBLIC_API_PORT=8010
set API_PORT=8010
```

### 4) Optional: RAG indexing

```bash
curl -X POST http://127.0.0.1:8000/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{"source_type":"repo","root_path":".","index":"graphguard"}'

curl -X POST http://127.0.0.1:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"question":"How does Kafka flow into Neo4j?","index":"graphguard"}'
```

## Live Demo vs Local Stack

- Hosted demo (free tier): Planned on Supabase + Upstash + Railway with heavyweight services disabled.
- Full pipeline (local): Kafka, Neo4j, Flink, MLflow, and Grafana run via Docker Compose.

## Architecture

```
Sources -> Kafka -> Flink CEP -> Feature Store -> ML Scoring
                         |              |            |
                         |              |            +-> FastAPI + GraphQL
                         |              +-> Neo4j Graph
                         +-> Spark/Feast

UI (Next.js + D3) -> GraphQL -> Fraud Queue -> SHAP + RAG
```

## API

### REST (FastAPI)

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | /score | Score a transaction |
| GET | /health | Health check |
| GET | /metrics | Prometheus metrics |
| POST | /rag/ingest | Build a local RAG index |
| POST | /rag/query | Query the RAG index |

### GraphQL (Strawberry)

```graphql
query FraudQueue {
  fraudQueue(status: PENDING, limit: 20) {
    items {
      id
      transactionId
      userId
      amountVal
      currencyCode
      fraudScore
    }
  }
}
```

## Testing

```bash
pytest -v
```

Local test evidence is stored under `docs/evidence/` (for example, `docs/evidence/python-tests-20260124-210457.txt`).

## Tech Stack (Summary)

- Frontend: Next.js 16, React 18, TypeScript, D3, Tailwind
- Backend: FastAPI, Strawberry GraphQL, Pydantic, Redis
- Data: Kafka, Flink, Spark, Feast, Neo4j, PostgreSQL
- ML: XGBoost, PyTorch, SHAP, MLflow
- Ops: Docker Compose, Prometheus, Grafana
- RAG: SentenceTransformers, pgvector, Groq/Ollama options

## Project Structure

```
graphguard/
  data-eng/           # Ingestion, streaming, features, graph
  ml/                 # Training, serving, explainability
  backend/            # GraphQL schema + resolvers
  frontend/           # Next.js UI
  infrastructure/     # Infra templates + configs
  tests/              # Unit + integration tests
  docker-compose.yml  # Local stack
```

## License

MIT
