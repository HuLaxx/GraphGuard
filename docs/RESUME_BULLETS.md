# GraphGuard - Resume Bullet Points

## Project Title
**GraphGuard: Real-Time Transaction Fraud Detection with Explainable Graph AI**

---

## Data Engineer

- Built a **Kafka → Flink → Neo4j/Feast** streaming pipeline to materialize 200+ graph/temporal features with sub-100ms freshness.
- Implemented **point-in-time joins** in Feast to prevent feature leakage across offline/online stores.
- Automated **S3/Parquet/Delta partitioning** and backfills via Airflow DAGs for daily model retraining.
- Added **Great Expectations** data quality checks to enforce schema validation and anomaly detection on transaction streams.

---

## Data Scientist

- Developed **XGBoost + Graph Attention Network (GAT)** baselines, achieving +35% fraud catch rate with 60% fewer false positives.
- Optimized for **AUC-PR** using temporal validation splits, SMOTE oversampling, and class-imbalance weighting.
- Delivered **SHAP-based explanations** to satisfy GDPR/FCRA "right to explanation" requirements for model decisions.
- Detected novel fraud rings via **Louvain community detection** and PageRank centrality analysis on transaction graphs.

---

## AI/ML Engineer

- Productionized **ensemble inference** in FastAPI with Redis feature caching for <50ms P95 latency.
- Implemented **MLflow model registry**, versioning, and A/B testing with consistent-hash traffic splitting.
- Scaled **GNN training** with PyTorch Geometric to handle 100M+ transaction graphs.
- Monitored **data drift** and model latency with Evidently AI and Prometheus, triggering automated retraining alerts.

---

## Full Stack Developer

- Built an **investigator console** in Next.js 14 + D3.js with interactive subgraph views and SHAP explanation dashboards.
- Implemented **GraphQL + FastAPI** APIs with Strawberry typed schemas and role-based access control.
- Integrated **case management workflows** with audit trail views for compliance reviews.
- Optimized UI for **high-volume alert triage**, reducing investigator decision time with priority-based queuing.

---

## Software Engineer

- Designed **containerized microservices** with Docker Compose and Terraform for reproducible multi-environment deployments.
- Built **high-throughput Neo4j queries** with composite indexes achieving sub-50ms graph traversals.
- Implemented **structured logging** (structlog) and Prometheus metrics for full-stack observability.
- Automated **CI/CD pipelines** and infrastructure provisioning with Terraform modules for local/cloud parity.

---

## One-Liner Summary (for LinkedIn/Headline)

> Built an enterprise fraud detection platform combining XGBoost, Graph Neural Networks, and real-time streaming (Kafka/Flink) to detect 35% more fraud with 60% fewer false positives.

---

## Technical Keywords (ATS Optimization)

`Python` `TypeScript` `Kafka` `Flink` `Neo4j` `GraphQL` `FastAPI` `Next.js` `React` `D3.js` `XGBoost` `PyTorch` `Graph Neural Networks` `SHAP` `MLflow` `Feast` `Airflow` `Redis` `Docker` `Terraform` `Prometheus` `PostgreSQL`
