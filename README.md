# GraphGuard: Enterprise Fraud Detection Platform

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Real-Time Transaction Network Fraud Detection with Explainable Graph AI**

GraphGuard is an enterprise-grade fraud detection platform that combines traditional machine learning (XGBoost) with Graph Neural Networks (GAT) to detect sophisticated fraud patterns in real-time transaction networks.

---

## 🎯 Key Features

- **Real-Time Detection**: Sub-100ms fraud scoring via FastAPI + Redis caching
- **Graph Intelligence**: Neo4j graph algorithms (PageRank, Louvain communities) for network analysis
- **Explainable AI**: SHAP-based explanations for every fraud decision
- **Interactive Dashboard**: React + D3.js network visualization for investigators
- **MLOps Ready**: MLflow tracking, Evidently AI drift detection, automated retraining

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Transaction   │────▶│      Kafka      │────▶│   Spark/Flink   │
│    Producer     │     │   (Ingestion)   │     │   (Features)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React + D3    │◀────│   FastAPI +     │◀────│   Neo4j Graph   │
│   Dashboard     │     │   GraphQL API   │     │   Algorithms    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  XGBoost + GAT  │
                        │   Ensemble      │
                        └─────────────────┘
```

---

## 📁 Project Structure

```
graphguard/
├── data-eng/                    # Track 1: Data Engineering
│   ├── producers/               # Kafka transaction producer
│   ├── consumers/               # Graph builder consumer
│   ├── neo4j/                   # Graph algorithms + export
│   ├── spark/                   # Feature engineering
│   ├── feast/                   # Feature store
│   ├── airflow/                 # DAG orchestration
│   └── great_expectations/      # Data quality
│
├── ml/                          # Track 2 & 3: Data Science + ML Engineering
│   ├── training/                # XGBoost, GAT, Ensemble models
│   ├── explainability/          # SHAP analysis, graph visualization
│   ├── serving/                 # FastAPI, caching, A/B testing
│   ├── monitoring/              # Prometheus, drift detection
│   └── pipelines/               # Automated retraining
│
├── backend/                     # Track 4: Full-Stack
│   └── graphql/                 # Strawberry GraphQL API
│
├── frontend/                    # Track 4: Full-Stack
│   └── src/components/          # React + D3.js components
│
├── infra/                       # Infrastructure
│   ├── terraform/               # AWS EKS provisioning
│   └── helm/                    # Kubernetes charts
│
├── tests/                       # Test suites
│   ├── unit/                    # Unit tests
│   └── integration/             # Integration tests
│
├── docker-compose.yml           # Local development stack
└── README.md                    # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+
- Node.js 18+

### 1. Start Infrastructure

```bash
# Copy .env.example to .env and set secrets
cp .env.example .env

# Start all services (Kafka, Neo4j, Redis, PostgreSQL)
docker-compose up -d

# Verify services
docker-compose ps
```

### 2. Install Dependencies

```bash
# Python dependencies
pip install -e "data-eng[dev]"
pip install -e "ml[dev]"

# Frontend dependencies
cd frontend && npm install
```

### 3. Initialize Feature Store

```bash
# Apply Feast feature definitions
cd data-eng/feast/feature_repo
feast apply
```

### 4. Run the API

```bash
# Start FastAPI server
cd ml/serving
uvicorn api:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Start Frontend

```bash
cd frontend
npm run dev
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=ml --cov=data-eng --cov-report=html

# Run specific test suite
pytest tests/unit/test_models.py -v
```

---

## 📊 Model Performance

| Metric | XGBoost | GAT | Ensemble |
|--------|---------|-----|----------|
| ROC-AUC | 0.93 | 0.89 | **0.95** |
| Precision@90%Recall | 0.82 | 0.78 | **0.85** |
| F1 Score | 0.84 | 0.80 | **0.87** |
| Inference Latency | 10ms | 25ms | 35ms |

---

## 🔧 Configuration

### Environment Variables

```bash
# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
SCHEMA_REGISTRY_URL=http://localhost:8081

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=graphguard_dev

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# MLflow
MLFLOW_TRACKING_URI=http://localhost:5000

# Model paths
XGB_MODEL_PATH=models/xgboost_fraud.json
GAT_MODEL_PATH=models/gat_fraud.pth

# API
API_KEY=change-me
CORS_ALLOW_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_GRAPHQL_URL=http://localhost:8000/graphql
NEXT_PUBLIC_API_KEY=change-me
```

---

## 📡 API Endpoints

### REST API (FastAPI)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/score` | POST | Score transaction for fraud |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

### GraphQL API

```graphql
query FraudQueue {
  fraudQueue(status: PENDING, limit: 50) {
    items {
      id
      fraudScore
      transaction { amount merchant { name } }
    }
    totalCount
  }
}

mutation LabelCase {
  labelCase(id: "case_123", label: FRAUD, notes: "Confirmed by customer") {
    id
    status
  }
}
```

---

## 🛠️ Development

### Running Neo4j Graph Algorithms

```bash
# Execute graph algorithms
cypher-shell -f data-eng/neo4j/graph_algorithms.cypher
```

### Training Models

```bash
# Train XGBoost baseline
python -m ml.training.baseline_xgboost --input data/features.parquet --output models/xgboost.json

# Train GAT model
python -m ml.training.gat_model --epochs 100 --output models/gat.pth
```

### Monitoring

- **Grafana**: http://localhost:3000 (admin/admin)
- **MLflow**: http://localhost:5000
- **Neo4j Browser**: http://localhost:7474

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Neo4j Graph Data Science Library
- PyTorch Geometric for GNN implementation
- SHAP for model explainability
- Evidently AI for drift detection
