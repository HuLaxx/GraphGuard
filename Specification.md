# **PROJECT 2: GRAPHGUARD - ENTERPRISE FRAUD DETECTION PLATFORM**

## **I. Executive Summary**

### **Project Title**
**GraphGuard: Real-Time Transaction Network Fraud Detection with Explainable Graph AI**

### **Real-World Problem Statement**
Financial fraud costs global businesses $5.1 trillion annually (2023 UN estimate). Traditional fraud detection systems suffer from critical limitations:
- **Feature-blind**: Analyze transactions in isolation, missing network patterns (collusion rings, money mules)
- **High false positives**: 90% of fraud alerts are false, causing alert fatigue and $100B+ in legitimate transaction blocks
- **Black box**: ML models lack explainability, violating regulations (GDPR Right to Explanation, FCRA)
- **Delayed detection**: Batch processing means fraud is detected hours/days after it occurs
- **Adversarial brittleness**: Fraudsters quickly adapt to rule-based systems

**Business Value**: GraphGuard provides institutional-grade fraud detection that:
- **Increases fraud catch rate by 35%** through graph-based network analysis (vs traditional models)
- **Reduces false positives by 60%** using ensemble models + SHAP explainability
- **Provides real-time scoring** (<100ms p99 latency) for transaction approval decisions
- **Ensures regulatory compliance** with full audit trails and human-readable explanations
- **Detects novel attack patterns** through unsupervised anomaly detection on transaction graphs
- **Saves $50M+ annually** for mid-sized payment processors through early fraud prevention

### **High-Level Solution**
GraphGuard is an enterprise-grade fraud detection platform that models the financial ecosystem as a dynamic, heterogeneous graph where users, merchants, devices, and bank accounts are nodes connected by transaction edges. The system implements a hybrid architecture combining **classical ML baselines** (XGBoost on tabular features) with **Graph Neural Networks** (GAT, GraphSAGE) that leverage network topology to detect sophisticated fraud patterns invisible to traditional models.

The data engineering layer ingests transaction streams via Kafka, constructs real-time graph snapshots in Neo4j, and materializes 200+ features (graph centrality, community membership, temporal patterns) into a Feast feature store. The ML pipeline trains daily on 100M+ transactions using Ray for distributed training, with MLflow tracking every experiment and Evidently AI monitoring production drift. A FastAPI inference API serves predictions in <50ms by caching hot features in Redis and using pre-computed graph embeddings. The frontend provides fraud investigators with an interactive network visualization (D3.js) showing suspicious subgraphs, SHAP explanation dashboards, and case management workflows. Every decision is logged to an immutable audit trail (PostgreSQL + blockchain hash anchoring) to satisfy SOC2, PCI-DSS, and GDPR requirements.

---

## **II. Technical Stack & Granular Details**

### **Languages**
- **Python 3.11+**: Data engineering, ML training, API services
- **Rust**: High-performance graph traversal microservice (optional for <10ms queries)
- **TypeScript 5.2+**: Full-stack (React, API types, shared schemas)
- **Cypher**: Neo4j query language for graph operations
- **SQL**: Feature transformations, audit queries
- **GraphQL**: API layer for complex nested queries

### **Frameworks**

**Backend:**
- **FastAPI 0.104+**: Main API gateway, real-time scoring endpoint
- **Celery 5.3**: Asynchronous task queue (batch investigations, report generation)
- **PyTorch 2.1**: Deep learning framework
- **PyTorch Geometric 2.4**: Graph Neural Networks
- **DGL (Deep Graph Library) 1.1**: Alternative GNN framework
- **NetworkX 3.2**: Graph analysis algorithms (centrality, community detection)
- **scikit-learn 1.3**: Classical ML baselines
- **XGBoost 2.0**: Gradient boosting baseline
- **SHAP 0.44**: Model explainability
- **LIME 0.2**: Local interpretable explanations (alternative)

**Frontend:**
- **React 18.2**: SPA with TypeScript
- **Next.js 14** (Alternative): SSR for SEO-heavy pages
- **Apollo Client 3.8**: GraphQL state management
- **D3.js 7.8**: Network graph visualizations
- **Cytoscape.js 3.26**: Alternative graph library
- **Recharts 2.10**: Statistical charts (precision-recall curves)
- **Material-UI 5.14**: Component library
- **React Query 5.0**: Server state caching

**Data Engineering:**
- **Apache Kafka 3.6**: Event streaming (transactions, user events)
- **Apache Flink 1.18**: Complex event processing (CEP) for pattern detection
- **Apache Airflow 2.7**: Orchestration (daily retraining, feature backfills)
- **dbt 1.7**: SQL transformations, data quality tests
- **Great Expectations 0.18**: Data validation framework
- **Debezium 2.4**: CDC from transactional databases

**ML/DS:**
- **Ray 2.7**: Distributed training and hyperparameter tuning
- **Optuna 3.5**: Bayesian hyperparameter optimization
- **MLflow 2.8**: Experiment tracking, model registry
- **Feast 0.35**: Feature store for online/offline serving
- **Evidently AI 0.4**: ML monitoring, drift detection
- **DVC 3.30**: Data versioning
- **Weights & Biases** (Alternative): Advanced experiment tracking
- **Prophet 1.1**: Time-series decomposition (fraud trend analysis)

### **Infrastructure**

**Container Orchestration:**
- **Kubernetes 1.28** (EKS/GKE): Microservices deployment
- **Helm 3.13**: Package management
- **Istio 1.19**: Service mesh (mTLS, traffic splitting for A/B tests)
- **ArgoCD 2.9**: GitOps continuous deployment

**Infrastructure as Code:**
- **Terraform 1.6**: Multi-cloud provisioning (AWS/GCP)
- **Pulumi** (Alternative): TypeScript-based IaC

**Cloud Services (AWS Primary):**
- **EKS**: Kubernetes cluster for microservices
- **RDS Aurora PostgreSQL**: Transactional data, audit logs
- **DocumentDB**: MongoDB-compatible (user profiles, investigation notes)
- **Neptune**: Managed graph database (alternative to self-hosted Neo4j)
- **ElastiCache Redis**: Feature cache, rate limiting
- **MSK**: Managed Kafka
- **S3**: Data lake (raw transactions, model artifacts, investigation evidence)
- **Lambda**: Serverless webhooks (Plaid, Stripe integrations)
- **SageMaker**: Model training (alternative to Ray on EKS)
- **DynamoDB**: High-speed key-value store (fraud rule cache)
- **CloudWatch + X-Ray**: Metrics, distributed tracing
- **Kinesis Data Streams**: Real-time analytics (alternative to Kafka)
- **Secrets Manager**: API keys, database credentials
- **WAF**: API protection against injection attacks
- **Cognito**: User authentication (investigators, admins)

**GCP Services (Multi-Cloud):**
- **GKE**: Kubernetes cluster
- **Cloud Spanner**: Globally distributed SQL (for multi-region deployments)
- **BigQuery**: Data warehouse for historical analytics
- **Vertex AI**: Model training and serving
- **Pub/Sub**: Messaging (alternative to Kafka for GCP-native)

### **Data Stores**

**Relational:**
- **PostgreSQL 16 (Aurora)**: 
  - Tables: `transactions`, `users`, `merchants`, `devices`, `fraud_cases`, `audit_logs`
  - Extensions: `pg_trgm` (fuzzy string matching), `postgis` (geospatial queries)
  - Partitioning: Range partition `transactions` by date (monthly)

**Graph:**
- **Neo4j 5.13** (Community or Enterprise on K8s):
  - Nodes: `User`, `Merchant`, `Device`, `BankAccount`, `IPAddress`
  - Relationships: `TRANSACTED_WITH`, `USED_DEVICE`, `FROM_IP`, `SHARED_DEVICE`
  - Indexes: Composite index on `(User, Merchant, timestamp)`
  - Plugins: APOC (graph algorithms), GDS (Graph Data Science library)
  - Alternative: **AWS Neptune** (managed, but proprietary Gremlin/SPARQL)

**NoSQL:**
- **MongoDB (DocumentDB)**: 
  - Collections: `user_profiles`, `investigation_notes`, `fraud_patterns`
  - Use case: Flexible schemas for investigator annotations
- **Redis (ElastiCache)**:
  - Cache: Feature vectors (user embedding, merchant stats)
  - Data structures: Sorted sets (recent transactions), HyperLogLog (unique device count)
  - TTL: 15 minutes for hot features

**Vector:**
- **Qdrant 1.7** (self-hosted on K8s): 
  - Transaction embeddings for similarity search
  - Use case: "Find transactions similar to this fraud case"
- Alternative: **Weaviate**, **Milvus**

**Data Lake:**
- **S3**: 
  - Raw zone: CSV/JSON from payment gateways (immutable)
  - Processed zone: Parquet files (partitioned by date, transaction_type)
  - Feature zone: Feast offline store (Parquet with time-travel)
  - Model zone: MLflow artifacts (model weights, training logs)
- **Delta Lake 3.0**: ACID transactions on S3, time-travel queries
- Alternative: **Apache Iceberg** (better schema evolution)

**Feature Store:**
- **Feast 0.35**:
  - Online store: Redis (for real-time serving <1ms)
  - Offline store: S3 Parquet (for training)
  - Feature views: `user_features`, `merchant_features`, `transaction_features`, `graph_features`
  - Point-in-time joins: Prevents feature leakage

**Time-Series:**
- **TimescaleDB** (PostgreSQL extension):
  - Continuous aggregates: Pre-compute hourly fraud rates
  - Retention policies: Auto-delete data >2 years
- Alternative: **InfluxDB** for pure time-series workloads

### **DevOps/MLOps Tools**

**CI/CD:**
- **GitHub Actions**: Build, test, deploy
- **ArgoCD**: GitOps for K8s (declarative deployments)
- **FluxCD** (Alternative): GitOps alternative

**ML Lifecycle:**
- **MLflow 2.8**: 
  - Experiment tracking with S3 backend
  - Model registry with staging/production stages
  - Model serving with MLflow Models (alternative to TorchServe)
- **DVC 3.30**: Version large datasets, model checkpoints
- **Feast 0.35**: Online/offline feature store
- **Great Expectations 0.18**: Data quality validation suites
- **Evidently AI 0.4**: 
  - Data drift detection (Kolmogorov-Smirnov test)
  - Model drift detection (prediction distribution shifts)
  - Reports: HTML dashboards stored in S3

**Orchestration:**
- **Airflow 2.7**: 
  - DAGs: Daily retraining, feature backfills, drift monitoring
  - Executor: Celery (for parallel task execution)
  - Backend: PostgreSQL (metadata store)
- **Prefect** (Alternative): Modern workflow engine with dynamic DAGs

**Observability:**
- **Prometheus 2.48**: Metrics scraping (API latency, model inference time)
- **Grafana 10.2**: Dashboards (business metrics, system health)
- **Loki 2.9**: Log aggregation (structured JSON logs)
- **Tempo 2.3**: Distributed tracing (alternative to X-Ray)
- **OpenTelemetry SDK**: Instrumentation for Python/TypeScript
- **Sentry 23.11**: Error tracking, alerting
- **PagerDuty**: On-call incident management

**Security:**
- **HashiCorp Vault 1.15**: Secrets management
- **Falco**: Runtime security (detect malicious container activity)
- **Trivy**: Container vulnerability scanning
- **OWASP ZAP**: Automated security testing (API penetration testing)
- **Snyk**: Dependency vulnerability scanning
- **AWS GuardDuty**: Threat detection
- **AWS Macie**: PII/PCI data discovery and protection

### **Libraries (The "Small Details")**

**Python Backend:**
```python
# API & Validation
fastapi==0.104.1
pydantic==2.5.0
pydantic-settings==2.1.0
graphene==3.3  # GraphQL schema

# Database
sqlalchemy==2.0.23
alembic==1.13.0
asyncpg==0.29.0
psycopg2-binary==2.9.9
neo4j==5.14.0  # Neo4j driver
py2neo==2021.2.3  # Alternative Neo4j client

# Graph Analysis
networkx==3.2.1
python-igraph==0.11.3  # Faster than NetworkX
graph-tool==2.57  # C++ backend, 100x faster

# ML
torch==2.1.2
torch-geometric==2.4.0
dgl==1.1.3  # Deep Graph Library
xgboost==2.0.3
scikit-learn==1.3.2
shap==0.44.0
lime==0.2.0.1
imbalanced-learn==0.11.0  # SMOTE

# Feature Store
feast[redis,aws]==0.35.0

# Distributed Computing
ray[default]==2.7.1
celery[redis]==5.3.4

# Data Processing
pandas==2.1.4
polars==0.19.19  # 10x faster than pandas
pyarrow==14.0.2
duckdb==0.9.2

# Kafka
confluent-kafka==2.3.0
faust-streaming==0.11.0  # Kafka Streams for Python

# MLOps
mlflow==2.8.1
evidently==0.4.11
great-expectations==0.18.5
dvc==3.30.0

# Monitoring
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0
prometheus-client==0.19.0
sentry-sdk[fastapi]==1.39.1

# Auth & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
cryptography==41.0.7

# Utils
tenacity==8.2.3  # Retry logic
pydantic-yaml==1.2.0
python-dotenv==1.0.0
structlog==23.2.0
faker==20.1.0  # Generate synthetic data
```

**TypeScript Frontend:**
```json
{
  "dependencies": {
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "@apollo/client": "3.8.8",
    "graphql": "16.8.1",
    "d3": "7.8.5",
    "cytoscape": "3.26.0",
    "cytoscape-cola": "2.5.1",  // Force-directed layout
    "@mui/material": "5.14.20",
    "@emotion/react": "11.11.1",
    "@emotion/styled": "11.11.0",
    "recharts": "2.10.3",
    "@tanstack/react-query": "5.17.0",
    "@tanstack/react-table": "8.11.2",
    "zod": "3.22.4",
    "zustand": "4.4.7",
    "date-fns": "2.30.0",
    "react-hook-form": "7.49.2",
    "react-hot-toast": "2.4.1",
    "framer-motion": "10.16.16"
  },
  "devDependencies": {
    "typescript": "5.3.3",
    "@types/react": "18.2.45",
    "@types/d3": "7.4.3",
    "vite": "5.0.8",
    "vitest": "1.0.4",
    "@testing-library/react": "14.1.2",
    "playwright": "1.40.1",
    "eslint": "8.56.0",
    "prettier": "3.1.1"
  }
}
```

---

## **III. System Architecture & Design**

### **High-Level Architecture**

**Architecture Style**: **Event-Driven Microservices with CQRS + Graph Database**

```
┌──────────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER (Fraud Investigators)             │
│   React SPA + Apollo GraphQL + D3.js Network Visualization       │
└────────────────────┬─────────────────────────────────────────────┘
                     │ HTTPS / GraphQL
┌────────────────────▼─────────────────────────────────────────────┐
│                  API GATEWAY (Kong + WAF)                         │
│  Auth │ Rate Limiting │ Request Logging │ GraphQL Endpoint       │
└──┬────────────────┬──────────────────────┬────────────────────────┘
   │                │                      │
   ▼                ▼                      ▼
┌──────────┐  ┌──────────┐        ┌──────────────────┐
│ Auth Svc │  │ GraphQL  │        │ Scoring API      │
│ (Cognito)│  │ Gateway  │        │ (FastAPI)        │
└──────────┘  │ (FastAPI)│        │ <100ms SLA       │
              └────┬─────┘        └────────┬─────────┘
                   │                       │
        ┌──────────┴───────┐      ┌───────┴──────┐
        │                  │      │              │
        ▼                  ▼      ▼              ▼
   ┌─────────┐      ┌──────────────┐    ┌──────────────┐
   │ User Svc│      │ Case Mgmt Svc│    │ Feature Svc  │
   │ (CRUD)  │      │ (GraphQL)    │    │ (Feast API)  │
   └────┬────┘      └──────┬───────┘    └──────┬───────┘
        │                  │                    │
        ▼                  ▼                    ▼
   ┌─────────────────────────────────────────────────┐
   │            COMMAND STORE (Write Path)            │
   │  Kafka Topics: transactions, fraud_labels        │
   └──────────┬──────────────────┬───────────────────┘
              │                  │
     ┌────────▼────┐    ┌────────▼─────────┐
     │ Transaction │    │ Graph Builder    │
     │ Processor   │    │ (Kafka → Neo4j)  │
     │ (Flink CEP) │    └────────┬─────────┘
     └────────┬────┘             │
              │                  ▼
              │         ┌─────────────────┐
              │         │    Neo4j         │
              │         │  Graph Database  │
              │         │  (Users, Txns)   │
              │         └─────────┬────────┘
              │                   │
              ▼                   ▼
   ┌──────────────────────────────────────┐
   │      FEATURE ENGINEERING             │
   │  Spark Jobs (Airflow) + Feast Store  │
   └──────────┬───────────────────────────┘
              │
     ┌────────┴────────┐
     ▼                 ▼
┌──────────┐    ┌──────────────┐
│PostgreSQL│    │  Redis Cache │
│(Read Reps│    │  + Feature   │
│ for query│    │  Vectors     │
└──────────┘    └──────────────┘
                       │
              ┌────────┴────────┐
              ▼                 ▼
     ┌──────────────┐    ┌──────────────┐
     │ ML Training  │    │ ML Inference │
     │ (Ray + MLflow│    │ (TorchServe/ │
     │  on K8s)     │    │  FastAPI)    │
     └──────┬───────┘    └──────┬───────┘
            │                   │
            ▼                   ▼
     ┌──────────────────────────────┐
     │   MODEL REGISTRY (MLflow)    │
     │   S3 Backend + Versioning    │
     └──────────────────────────────┘
```

**Key Components:**

1. **Ingestion Layer** (Data Engineering):
   - **Transaction Stream**: Kafka producers from payment gateways (Stripe, Plaid, internal systems)
   - **User Events**: Login attempts, profile changes, KYC updates
   - **External Feeds**: Sanctions lists (OFAC), stolen card databases, fraud intelligence feeds

2. **Event Backbone** (Data Engineering):
   - **Kafka Topics**: 
     - `transactions.raw` (schema: TransactionEvent)
     - `transactions.enriched` (with feature engineering)
     - `fraud.labels` (ground truth from investigators)
     - `model.predictions` (inference results for auditing)
   - **Schema Registry**: Avro schemas with version control

3. **Stream Processing** (Data Engineering + ML):
   - **Flink CEP**: Complex Event Processing for rule-based patterns
     - Pattern: "5+ failed login attempts in 60s" → Lock account
     - Pattern: "Transaction from new device + new merchant + high amount" → High risk score
   - **Kafka Streams**: Real-time aggregations (transaction velocity per user)

4. **Graph Construction** (Data Engineering):
   - **Kafka → Neo4j**: Consumer writes transactions as graph edges
   - **Batch Jobs** (Airflow): Daily full graph rebuild from PostgreSQL
   - **Incremental Updates**: Real-time edge insertion on new transactions

5. **Feature Engineering** (Data Engineering + DS):
   - **Spark Jobs**: 
     - Tabular features: Transaction amount stats, user velocity, merchant risk score
     - Graph features: PageRank, betweenness centrality, community membership
   - **Feast Feature Store**:
     - Online store (Redis): Real-time features (<1ms retrieval)
     - Offline store (S3): Historical features for training

6. **ML Training** (MLE):
   - **Ray Cluster**: Distributed training on K8s
   - **Models**:
     - Baseline: XGBoost on tabular features
     - Advanced: Graph Attention Network (GAT) on transaction graph
     - Ensemble: Stacking XGBoost + GAT predictions
   - **MLflow**: Experiment tracking, model versioning

7. **ML Serving** (MLE):
   - **FastAPI**: REST endpoint `/score` (latency SLA: <100ms p99)
   - **Feature Caching**: Redis cache for frequently accessed users
   - **Model Versioning**: A/B test champion vs challenger models

8. **Explainability** (DS + MLE):
   - **SHAP**: Feature importance for every prediction
   - **Graph Visualization**: D3.js renders suspicious subgraphs
   - **Counterfactual**: "If amount was $X less, prediction would be safe"

9. **API Layer** (SE):
   - **GraphQL Gateway**: Single endpoint for complex nested queries
   - **REST API**: `/score` endpoint for real-time scoring
   - **WebSocket**: Live updates for ongoing investigations

10. **Frontend** (SE):
    - **React SPA**: Case management, fraud queue, analytics dashboards
    - **D3.js Network Graph**: Interactive visualization of transaction networks
    - **SHAP Dashboard**: Bar charts showing top features driving each prediction

11. **Audit & Compliance** (All):
    - **Immutable Logs**: Every prediction logged to PostgreSQL with blockchain hash
    - **GDPR**: Data retention policies (2 years), right to explanation
    - **SOC2**: Access controls, audit trails, encryption at rest/transit

### **Data Flow & Orchestration**

**Scenario: Real-Time Transaction Scoring**

```
1. TRANSACTION INITIATED (External Payment Gateway)
   └─> Stripe webhook → Lambda → Kafka topic: `transactions.raw`

2. EVENT VALIDATION (Data Engineering)
   └─> Kafka Consumer (Python)
       ├─> Schema validation (Avro)
       ├─> Deduplication (idempotency key in Redis)
       └─> Publish to `transactions.enriched`

3. FEATURE ENRICHMENT (Data Engineering)
   └─> Flink Job consumes `transactions.enriched`
       ├─> Join with user profile (PostgreSQL)
       ├─> Compute velocity features (transactions in last 1h, 24h, 7d)
       ├─> Lookup merchant risk score (Redis cache)
       └─> Publish to `transactions.features`

4. GRAPH UPDATE (Data Engineering)
   └─> Neo4j Consumer (Python + neo4j-driver)
       ├─> Create/update User node
       ├─> Create/update Merchant node
       ├─> Create TRANSACTED_WITH edge (properties: amount, timestamp)
       ├─> Run Cypher query: MATCH (u:User)-[r:TRANSACTED_WITH]->(m:Merchant) WHERE r.timestamp > NOW() - duration('PT1H')
       └─> Store subgraph in cache

5. FEATURE RETRIEVAL (MLE)
   └─> FastAPI `/score` endpoint receives request
       ├─> Call Feast feature service
       │   ├─> Online store (Redis): Get cached features (user_id, merchant_id)
       │   ├─> Cache hit rate: 85%
       │   └─> Cache miss: Query PostgreSQL + cache result
       │
       ├─> Graph features from Neo4j:
       │   ├─> PageRank score of user
       │   ├─> Community ID (Louvain algorithm)
       │   ├─> Betweenness centrality
       │   └─> Cached: 1-hop neighbors list
       │
       └─> Combine: [tabular_features, graph_features] → Feature vector (128-dim)

6. MODEL INFERENCE (MLE)
   └─> FastAPI calls model ensemble:
       ├─> Model 1: XGBoost (tabular features only)
       │   └─> Prediction: 0.72 (fraud probability)
       │
       ├─> Model 2: GAT (graph features)
       │   ├─> Fetch 2-hop subgraph from Neo4j
       │   ├─> Convert to PyG Data object
       │   ├─> GNN inference (TorchServe)
       │   └─> Prediction: 0.85
       │
       └─> Ensemble (weighted average: 0.6*XGB + 0.4*GAT)
           └─> Final score: 0.776

7. EXPLAINABILITY (MLE)
   └─> Generate explanations:
       ├─> SHAP values (computed on-demand, cached for 15min)
       │   └─> Top features: [new_device=0.3, high_amount=0.25, velocity_1h=0.2]
       │
       ├─> Graph reasoning:
       │   └─> "User is in a community with 3 known fraudsters"
       │   └─> Neo4j query: MATCH (u:User {id: $user_id})-[:IN_COMMUNITY]->(c:Community)<-[:IN_COMMUNITY]-(f:User {fraud: true})
       │
       └─> Counterfactual:
           └─> "If amount < $500, prediction would be 0.45 (safe)"

8. RESPONSE DELIVERY (SE)
   └─> FastAPI returns JSON:
       {
         "transaction_id": "txn_123",
         "fraud_score": 0.776,
         "decision": "REVIEW",  // AUTO_APPROVE, REVIEW, AUTO_DECLINE
         "latency_ms": 87,
         "explanations": {
           "shap_values": [...],
           "graph_reasoning": "...",
           "counterfactual": "..."
         }
       }

9. AUDIT LOGGING (Compliance)
   └─> Write to `audit_logs` table (PostgreSQL):
       ├─> transaction_id, user_id, model_version, prediction, timestamp
       ├─> Compute hash: SHA256(transaction_id + prediction + timestamp)
       └─> Store hash on blockchain (Ethereum testnet) for immutability proof

10. INVESTIGATOR REVIEW (If decision = REVIEW)
    └─> Frontend polls GraphQL API:
        ├─> Query: fraudQueue { cases { id, score, user, merchant } }
        ├─> Investigator clicks case
        ├─> GraphQL resolver:
        │   ├─> Fetch transaction details (PostgreSQL)
        │   ├─> Fetch subgraph (Neo4j Cypher query)
        │   ├─> Fetch SHAP explanations (Redis cache or recompute)
        │   └─> Return nested JSON
        └─> Frontend renders:
            ├─> D3.js network graph (user → merchant → other users)
            ├─> SHAP bar chart (feature importance)
            ├─> Timeline (user's transaction history)
            └─> Case notes form (investigator adds comments)

11. FEEDBACK LOOP (Model Improvement)
    └─> Investigator labels case (fraud/legitimate)
        ├─> GraphQL mutation: labelCase(id, label)
        ├─> Publish to Kafka: `fraud.labels`
        ├─> Airflow DAG triggered (if 1000+ new labels)
        │   ├─> Fetch new training data from S3
        │   ├─> Retrain XGBoost + GAT (Ray cluster)
        │   ├─> Evaluate on hold-out test set
        │   ├─> If performance > production model:
        │   │   └─> Register to MLflow, tag as "challenger"
        │   └─> A/B test: Route 10% traffic to challenger
        └─> After 7 days: Statistical test (t-test on precision@90recall)
            └─> If challenger wins: Promote to production
```

**Critical Latency Budget (100ms Total):**
- Kafka produce/consume: 5ms
- Feast feature retrieval: 15ms (80% cache hit)
- Neo4j graph query: 30ms (1-hop neighbors, indexed)
- XGBoost inference: 10ms
- GAT inference: 25ms (pre-computed embeddings)
- SHAP values: 10ms (cached or approximated)
- Network latency: 5ms

### **Design Patterns**

1. **CQRS (Command Query Responsibility Segregation)**
   - **Write Model**: Kafka for event sourcing (immutable transaction log)
   - **Read Model**: PostgreSQL read replicas + Redis cache for queries
   - **Why**: Fraud scoring (read-heavy) optimized separately from transaction ingestion (write-heavy)

2. **Event Sourcing**
   - All state changes are events in Kafka: `TransactionCreated`, `FraudLabelApplied`, `ModelPredictionMade`
   - Rebuild state by replaying events (e.g., reconstruct graph from transaction history)
   - **Why**: Full audit trail, time-travel debugging, replay for model retraining

3. **Saga Pattern (Orchestration)**
   - Model retraining workflow (Airflow DAG):
     1. Fetch new data (Spark)
     2. Feature engineering (dbt + Spark)
     3. Train model (Ray)
     4. Evaluate (Python)
     5. Register (MLflow)
     6. Deploy (ArgoCD updates K8s)
   - Each step is a separate service; Airflow orchestrates
   - **Why**: Long-running workflow (4 hours), need failure recovery

4. **Repository Pattern**
   - Abstract data access: `TransactionRepository`, `UserRepository`
   ```python
   class TransactionRepository:
       async def get_by_id(self, txn_id: str) -> Transaction:
           ...
       async def get_user_transactions(self, user_id: str, limit: int) -> List[Transaction]:
           ...
   ```
   - **Why**: Swap PostgreSQL for DynamoDB without changing business logic

5. **Factory Pattern**
   - `ModelFactory.create(model_type="gat", version="v3")` → Returns trained model
   - **Why**: Support multiple model types (XGBoost, GAT, LightGBM) with same interface

6. **Strategy Pattern**
   - Explainability strategies: `SHAPExplainer`, `LIMEExplainer`, `GraphExplainer`
   - Runtime selection: `explainer = ExplainerFactory.create(method=config.explainer_method)`
   - **Why**: Different models need different explanation methods

7. **Circuit Breaker**
   - Neo4j queries wrapped in Tenacity circuit breaker
   ```python
   @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
   def query_neo4j(cypher: str):
       with neo4j_driver.session() as session:
           return session.run(cypher)
   ```
   - If Neo4j down: Fall back to cached graph embeddings (stale but available)
   - **Why**: Neo4j single point of failure → prevent cascade failures

8. **Bulkhead Pattern**
   - Separate thread pools:
     - Real-time scoring: 50 threads
     - Batch investigations: 10 threads
     - Background jobs: 5 threads
   - **Why**: Investigation queries (slow, complex) don't starve scoring API

9. **Materialized View Pattern**
   - PostgreSQL materialized views for expensive queries:
   ```sql
   CREATE MATERIALIZED VIEW daily_fraud_rates AS
   SELECT date, merchant_id, COUNT(*) FILTER (WHERE fraud = true) / COUNT(*) AS fraud_rate
   FROM transactions
   GROUP BY date, merchant_id;
   
   REFRESH MATERIALIZED VIEW daily_fraud_rates;  -- Run daily via Airflow
   ```
   - **Why**: Avoid scanning 100M row table on every dashboard load

10. **Graph Partitioning (Sharding)**
    - Neo4j sharded by user region: `neo4j-us`, `neo4j-eu`, `neo4j-asia`
    - Route queries based on `user.region`
    - **Why**: Single Neo4j instance hits 1TB graph size limit

### **Design Decisions (Trade-offs)**

| Decision | Chosen | Alternative | Rationale |
|----------|--------|-------------|-----------|
| **Graph DB** | Neo4j | Neptune (AWS) | Neo4j: Open-source, Cypher is expressive, GDS library. Neptune: Managed but proprietary Gremlin, vendor lock-in. |
| **GNN Library** | PyTorch Geometric | DGL (Deep Graph Library) | PyG: Better documentation, more tutorials. DGL: Faster for heterogeneous graphs but steeper learning curve. |
| **Feature Store** | Feast | Tecton | Feast: Open-source, AWS/GCP support. Tecton: Managed, better UI but $50K+/year. |
| **Stream Processing** | Flink CEP | Kafka Streams | Flink: Better for complex patterns (10+ conditions), event time processing. Kafka Streams: Simpler but limited CEP. |
| **Model Serving** | FastAPI + manual | TorchServe | FastAPI: More control, easier debugging. TorchServe: Better batching but heavier. Choose FastAPI for <1K QPS, TorchServe for >10K QPS. |
| **Frontend** | React SPA | Next.js SSR | React: Better for dashboards (no SEO needed). Next.js: Better for marketing site but unnecessary here. |
| **API** | GraphQL | REST | GraphQL: Single endpoint, flexible queries (avoid N+1). REST: Simpler but more endpoints. |
| **Monitoring** | Evidently AI | WhyLabs | Evidently: Open-source, HTML reports. WhyLabs: SaaS, alerting but $$$. |
| **Orchestration** | Airflow | Prefect | Airflow: Mature, large community, proven at scale. Prefect: Modern DX, dynamic DAGs but smaller community. |
| **Explainability** | SHAP | LIME | SHAP: Game theory, global consistency. LIME: Faster but local-only. Use SHAP for regulatory compliance. |

---

## **IV. Implementation Roadmap (The "Quad-Core" Integration)**

### **Phase 0: Foundation (Week 1-2)**

**All Tracks:**
- Monorepo setup: `pnpm workspaces` (backend, frontend, ml, data-eng)
- Terraform: VPC, EKS, RDS, MSK, ElastiCache, S3 buckets
- Deploy base services: Kafka, PostgreSQL, Redis, Neo4j (Helm charts)
- GitHub Actions: CI pipeline (lint, test, build)
- Observability: Prometheus, Grafana, Loki

---

### **1. Data Engineering Track (Week 3-8)**

#### **Week 3-4: Data Ingestion**

**Task 1.1: Kafka Transaction Producer**
```python
# File: data-eng/producers/transaction_ingester.py
# Goal: Ingest transactions from Stripe webhooks

from confluent_kafka import Producer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from pydantic import BaseModel
from datetime import datetime
import hashlib

class TransactionEvent(BaseModel):
    transaction_id: str
    user_id: str
    merchant_id: str
    amount: float
    currency: str
    timestamp: datetime
    device_id: str
    ip_address: str
    card_last4: str
    
    @property
    def idempotency_key(self) -> str:
        # Deterministic key to prevent duplicates
        return hashlib.sha256(
            f"{self.transaction_id}:{self.timestamp.isoformat()}".encode()
        ).hexdigest()

# Kafka producer config
producer_config = {
    'bootstrap.servers': 'kafka:9092',
    'acks': 'all',  # Wait for all replicas
    'enable.idempotence': True,  # Exactly-once semantics
    'max.in.flight.requests.per.connection': 5,
    'retries': 10
}

schema_registry = SchemaRegistryClient({'url': 'http://schema-registry:8081'})
avro_serializer = AvroSerializer(schema_registry, transaction_schema)

producer = Producer(producer_config)

def publish_transaction(txn: TransactionEvent):
    producer.produce(
        topic='transactions.raw',
        key=txn.idempotency_key.encode(),
        value=avro_serializer(txn.dict(), SerializationContext('transactions.raw', MessageField.VALUE)),
        on_delivery=delivery_callback
    )
    producer.flush()

# Gotcha: Stripe webhooks can duplicate - use idempotency_key
# Gotcha: Set compression='snappy' for 60% size reduction
```

**Task 1.2: Flink CEP for Pattern Detection**
```python
# File: data-eng/flink/fraud_patterns.py
# Technology: PyFlink (Python API for Apache Flink)
# Goal: Detect complex fraud patterns in real-time

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import KeyedProcessFunction, RuntimeContext
from pyflink.common.typeinfo import Types

env = StreamExecutionEnvironment.get_execution_environment()

# Pattern 1: Rapid-fire transactions (5+ in 60 seconds)
class RapidFireDetector(KeyedProcessFunction):
    def __init__(self):
        self.transactions = []
    
    def process_element(self, value, ctx: KeyedProcessFunction.Context):
        current_time = ctx.timestamp()
        user_id = value['user_id']
        
        # Remove old transactions (>60s ago)
        self.transactions = [t for t in self.transactions if current_time - t < 60000]
        
        self.transactions.append(current_time)
        
        if len(self.transactions) >= 5:
            yield {
                'pattern': 'RAPID_FIRE',
                'user_id': user_id,
                'count': len(self.transactions),
                'risk_score': 0.9
            }

# Pattern 2: High-value transaction from new device
class NewDeviceHighValueDetector(KeyedProcessFunction):
    def process_element(self, value, ctx):
        # Check if device_id seen before (query Redis)
        is_new_device = not redis_client.exists(f"device:{value['device_id']}")
        
        if is_new_device and value['amount'] > 1000:
            yield {
                'pattern': 'NEW_DEVICE_HIGH_VALUE',
                'user_id': value['user_id'],
                'amount': value['amount'],
                'device_id': value['device_id'],
                'risk_score': 0.85
            }

# Apply patterns
transactions = env.add_source(FlinkKafkaConsumer('transactions.raw', ...))

patterns = transactions \
    .key_by(lambda x: x['user_id']) \
    .process(RapidFireDetector()) \
    .union(transactions.key_by(lambda x: x['user_id']).process(NewDeviceHighValueDetector()))

patterns.add_sink(FlinkKafkaProducer('fraud.patterns', ...))

env.execute("Fraud Pattern Detection")

# Gotcha: Flink state grows unbounded - set TTL: state_ttl_config = StateTtlConfig.new_builder(Time.days(7)).build()
# Gotcha: Flink checkpoints to S3 for failure recovery
```

**Task 1.3: Graph Construction (Kafka → Neo4j)**
```python
# File: data-eng/consumers/graph_builder.py
# Goal: Build real-time transaction graph in Neo4j

from confluent_kafka import Consumer
from neo4j import GraphDatabase
import json

consumer_config = {
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'graph-builder',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False  # Manual commit for exactly-once
}

consumer = Consumer(consumer_config)
consumer.subscribe(['transactions.enriched'])

neo4j_driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "password"))

def create_transaction_edge(txn):
    with neo4j_driver.session() as session:
        session.run("""
            MERGE (u:User {id: $user_id})
            ON CREATE SET u.created_at = timestamp()
            
            MERGE (m:Merchant {id: $merchant_id})
            ON CREATE SET m.created_at = timestamp()
            
            MERGE (d:Device {id: $device_id})
            
            CREATE (u)-[:TRANSACTED_WITH {
                amount: $amount,
                timestamp: $timestamp,
                transaction_id: $transaction_id
            }]->(m)
            
            CREATE (u)-[:USED_DEVICE]->(d)
        """, 
        user_id=txn['user_id'],
        merchant_id=txn['merchant_id'],
        device_id=txn['device_id'],
        amount=txn['amount'],
        timestamp=txn['timestamp'],
        transaction_id=txn['transaction_id']
        )

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    
    txn = json.loads(msg.value().decode('utf-8'))
    
    try:
        create_transaction_edge(txn)
        consumer.commit(msg)  # Commit only after successful write
    except Exception as e:
        # DLQ: Send to dead-letter queue
        producer.produce('transactions.dlq', value=msg.value())
        consumer.commit(msg)

# Gotcha: Neo4j writes are slow (50-100ms) - batch 10-20 transactions per write
# Gotcha: Use MERGE instead of CREATE to avoid duplicate nodes
```

**Task 1.4: Neo4j Graph Algorithms**
```cypher
// File: data-eng/neo4j/graph_algorithms.cypher
// Goal: Compute graph features (centrality, community detection)

// 1. PageRank (identify influential users)
CALL gds.graph.project(
  'transaction-graph',
  'User',
  'TRANSACTED_WITH'
)
YIELD graphName;

CALL gds.pageRank.write('transaction-graph', {
  writeProperty: 'pagerank',
  maxIterations: 20,
  dampingFactor: 0.85
})
YIELD nodePropertiesWritten;

// 2. Louvain Community Detection (find fraud rings)
CALL gds.louvain.write('transaction-graph', {
  writeProperty: 'community_id'
})
YIELD communityCount, modularity;

// 3. Betweenness Centrality (find transaction hubs - potential money mules)
CALL gds.betweenness.write('transaction-graph', {
  writeProperty: 'betweenness'
})
YIELD centralityDistribution;

// 4. Label Propagation (semi-supervised fraud detection)
// Seed: Known fraudulent users
MATCH (u:User {fraud: true})
SET u.seed_label = 'fraud';

CALL gds.labelPropagation.write('transaction-graph', {
  seedProperty: 'seed_label',
  writeProperty: 'predicted_label',
  maxIterations: 10
})
YIELD nodePropertiesWritten;

// Gotcha: Run algorithms on projected in-memory graph (gds.graph.project), not Cypher queries (100x faster)
// Gotcha: Drop projection after: CALL gds.graph.drop('transaction-graph')
```

#### **Week 5-6: Feature Engineering**

**Task 1.5: Spark Feature Engineering**
```python
# File: data-eng/spark/feature_engineering.py
# Goal: Compute 200+ features for ML training

from pyspark.sql import SparkSession, Window
from pyspark.sql.functions import *

spark = SparkSession.builder \
    .appName("FraudFeatureEngineering") \
    .config("spark.jars.packages", "io.delta:delta-core_2.12:2.4.0") \
    .getOrCreate()

# Read raw transactions from S3
df = spark.read.format("delta").load("s3://graphguard/transactions/")

# 1. Temporal Features
window_1h = Window.partitionBy("user_id").orderBy("timestamp").rangeBetween(-3600, 0)
window_24h = Window.partitionBy("user_id").orderBy("timestamp").rangeBetween(-86400, 0)
window_7d = Window.partitionBy("user_id").orderBy("timestamp").rangeBetween(-604800, 0)

df = df.withColumn("txn_count_1h", count("*").over(window_1h))
df = df.withColumn("txn_count_24h", count("*").over(window_24h))
df = df.withColumn("txn_count_7d", count("*").over(window_7d))
df = df.withColumn("amount_sum_1h", sum("amount").over(window_1h))
df = df.withColumn("amount_sum_24h", sum("amount").over(window_24h))
df = df.withColumn("amount_mean_7d", mean("amount").over(window_7d))
df = df.withColumn("amount_std_7d", stddev("amount").over(window_7d))

# 2. Device Features
df = df.withColumn("device_first_seen", min("timestamp").over(Window.partitionBy("device_id")))
df = df.withColumn("device_age_days", (col("timestamp") - col("device_first_seen")) / 86400)
df = df.withColumn("device_user_count", approx_count_distinct("user_id").over(Window.partitionBy("device_id")))

# 3. Merchant Features
merchant_stats = df.groupBy("merchant_id").agg(
    avg("amount").alias("merchant_avg_amount"),
    stddev("amount").alias("merchant_std_amount"),
    (count(when(col("fraud") == True, 1)) / count("*")).alias("merchant_fraud_rate")
)
df = df.join(broadcast(merchant_stats), "merchant_id")

# 4. Geospatial Features
df = df.withColumn("prev_ip", lag("ip_address").over(Window.partitionBy("user_id").orderBy("timestamp")))
# Join with IP geolocation table to compute distance
df = df.withColumn("ip_distance_km", haversine_udf(col("ip_lat"), col("ip_lon"), col("prev_ip_lat"), col("prev_ip_lon")))
df = df.withColumn("impossible_travel", (col("ip_distance_km") > 1000) & ((col("timestamp") - lag("timestamp").over(Window.partitionBy("user_id").orderBy("timestamp"))) < 3600))

# Write to Feature Store (Feast offline store)
df.write.format("delta") \
    .mode("overwrite") \
    .partitionBy("date") \
    .save("s3://graphguard/features/")

# Gotcha: Window functions with unbounded FOLLOWING cause shuffle - use PRECEDING only
# Gotcha: Broadcast small tables (<10MB) to avoid shuffle joins
```

**Task 1.6: Graph Features Export**
```python
# File: data-eng/neo4j/export_graph_features.py
# Goal: Export computed graph features (PageRank, etc.) to Feast

from neo4j import GraphDatabase
import pandas as pd
from feast import FeatureStore

neo4j_driver = GraphDatabase.driver("bolt://neo4j:7687")

def export_graph_features():
    with neo4j_driver.session() as session:
        result = session.run("""
            MATCH (u:User)
            RETURN 
                u.id AS user_id,
                u.pagerank AS pagerank,
                u.community_id AS community_id,
                u.betweenness AS betweenness,
                SIZE((u)-[:TRANSACTED_WITH]->()) AS out_degree,
                SIZE((u)<-[:TRANSACTED_WITH]-()) AS in_degree
        """)
        
        df = pd.DataFrame([dict(record) for record in result])
    
    # Write to Feast offline store (S3 Parquet)
    df.to_parquet("s3://graphguard/features/graph_features.parquet")
    
    # Register with Feast
    store = FeatureStore(repo_path="feast_repo/")
    store.apply([
        Entity(name="user", join_keys=["user_id"]),
        FeatureView(
            name="graph_features",
            entities=["user"],
            schema=[
                Field(name="pagerank", dtype=Float32),
                Field(name="community_id", dtype=Int64),
                Field(name="betweenness", dtype=Float32),
                Field(name="out_degree", dtype=Int64),
                Field(name="in_degree", dtype=Int64)
            ],
            source=FileSource(path="s3://graphguard/features/graph_features.parquet")
        )
    ])

export_graph_features()

# Gotcha: Run graph algorithm computation in Neo4j, not in pandas (1000x faster)
# Gotcha: Export only necessary features - full graph export takes hours
```

**Task 1.7: Feast Feature Store Setup**
```python
# File: data-eng/feast/feature_repo/feature_store.yaml
project: graphguard
registry: s3://graphguard/feast/registry.db
provider: aws
online_store:
    type: redis
    connection_string: redis://elasticache:6379
offline_store:
    type: file
    path: s3://graphguard/features/

# File: data-eng/feast/feature_repo/features.py
from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Int64, String
from datetime import timedelta

user = Entity(name="user", join_keys=["user_id"], description="User entity")

# Transaction features
transaction_features = FeatureView(
    name="transaction_features",
    entities=[user],
    ttl=timedelta(days=365),
    schema=[
        Field(name="txn_count_1h", dtype=Int64),
        Field(name="txn_count_24h", dtype=Int64),
        Field(name="amount_sum_1h", dtype=Float32),
        Field(name="amount_mean_7d", dtype=Float32),
        Field(name="amount_std_7d", dtype=Float32),
    ],
    source=FileSource(
        path="s3://graphguard/features/transaction_features.parquet",
        timestamp_field="event_timestamp"
    ),
    online=True  # Materialize to Redis
)

# Graph features
graph_features = FeatureView(
    name="graph_features",
    entities=[user],
    ttl=timedelta(days=7),  # Update weekly
    schema=[
        Field(name="pagerank", dtype=Float32),
        Field(name="community_id", dtype=Int64),
        Field(name="betweenness", dtype=Float32)
    ],
    source=FileSource(path="s3://graphguard/features/graph_features.parquet"),
    online=True
)

# Deploy: feast apply
# Materialize to online store: feast materialize-incremental $(date -u +"%Y-%m-%dT%H:%M:%S")

# Gotcha: TTL determines how long features stay in Redis - set based on freshness requirements
# Gotcha: materialize-incremental only works if timestamp_field is properly set
```

#### **Week 7-8: Orchestration & Data Quality**

**Task 1.8: Airflow DAG for Daily Pipeline**
```python
# File: data-eng/airflow/dags/daily_feature_pipeline.py
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.providers.amazon.aws.operators.emr import EmrAddStepsOperator
from airflow.operators.python import PythonOperator
from airflow.providers.neo4j.operators.neo4j import Neo4jOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-eng',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email': ['oncall@graphguard.com'],
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    'daily_feature_pipeline',
    default_args=default_args,
    schedule_interval='@daily',
    catchup=False,
    max_active_runs=1
) as dag:
    
    # 1. Validate raw data
    validate_transactions = PythonOperator(
        task_id='validate_transactions',
        python_callable=run_great_expectations_suite,
        op_kwargs={'suite_name': 'transaction_quality'}
    )
    
    # 2. Spark feature engineering
    spark_features = SparkSubmitOperator(
        task_id='spark_feature_engineering',
        application='s3://graphguard/spark/feature_engineering.py',
        conn_id='spark_emr',
        conf={
            'spark.executor.instances': '10',
            'spark.executor.memory': '8g',
            'spark.executor.cores': '4'
        },
        application_args=['--date', '{{ ds }}']
    )
    
    # 3. Run Neo4j graph algorithms
    neo4j_algorithms = Neo4jOperator(
        task_id='run_graph_algorithms',
        neo4j_conn_id='neo4j_prod',
        sql="""
            CALL gds.pageRank.write('transaction-graph', {writeProperty: 'pagerank'});
            CALL gds.louvain.write('transaction-graph', {writeProperty: 'community_id'});
        """
    )
    
    # 4. Export graph features
    export_graph = PythonOperator(
        task_id='export_graph_features',
        python_callable=export_graph_features_to_feast
    )
    
    # 5. Materialize to Feast online store
    materialize_feast = PythonOperator(
        task_id='materialize_feast',
        python_callable=lambda: os.system('feast materialize-incremental $(date -u +"%Y-%m-%dT%H:%M:%S")')
    )
    
    # 6. Data quality checks on features
    validate_features = PythonOperator(
        task_id='validate_features',
        python_callable=run_great_expectations_suite,
        op_kwargs={'suite_name': 'feature_quality'}
    )
    
    # 7. Trigger model retraining (if validation passes)
    trigger_retraining = PythonOperator(
        task_id='trigger_model_retraining',
        python_callable=lambda: trigger_dag('model_retraining_pipeline', execution_date='{{ ds }}'),
        trigger_rule='all_success'
    )
    
    # DAG dependencies
    validate_transactions >> spark_features
    spark_features >> [neo4j_algorithms, export_graph]
    [neo4j_algorithms, export_graph] >> materialize_feast
    materialize_feast >> validate_features
    validate_features >> trigger_retraining

# Gotcha: Use catchup=False to avoid backfilling on first deploy
# Gotcha: max_active_runs=1 prevents concurrent DAG runs (data corruption risk)
```

**Task 1.9: Great Expectations Data Quality**
```python
# File: data-eng/great_expectations/checkpoints/transaction_quality.py
import great_expectations as gx
from great_expectations.core.batch import RuntimeBatchRequest

context = gx.get_context()

# Define datasource
datasource = context.sources.add_spark_s3(
    name="s3_transactions",
    bucket="graphguard",
    boto3_options={"region_name": "us-east-1"}
)

# Define expectations
suite = context.add_expectation_suite(expectation_suite_name="transaction_quality")

context.add_expectation(
    expectation_suite_name="transaction_quality",
    expectation_type="expect_column_values_to_not_be_null",
    kwargs={"column": "transaction_id"}
)

context.add_expectation(
    expectation_suite_name="transaction_quality",
    expectation_type="expect_column_values_to_be_between",
    kwargs={"column": "amount", "min_value": 0, "max_value": 1000000}
)

context.add_expectation(
    expectation_suite_name="transaction_quality",
    expectation_type="expect_column_values_to_be_in_set",
    kwargs={"column": "currency", "value_set": ["USD", "EUR", "GBP"]}
)

# Custom expectation: Transaction velocity anomaly
context.add_expectation(
    expectation_suite_name="transaction_quality",
    expectation_type="expect_column_max_to_be_below",
    kwargs={
        "column": "txn_count_1h",
        "max_value": 50,  # Flag if user has >50 txns in 1 hour
        "mostly": 0.99  # Allow 1% outliers
    }
)

# Run checkpoint
checkpoint = context.add_checkpoint(
    name="daily_transaction_validation",
    validations=[
        {
            "batch_request": RuntimeBatchRequest(
                datasource_name="s3_transactions",
                data_asset_name="transactions",
                runtime_parameters={"path": "s3://graphguard/transactions/{{ ds }}/*.parquet"}
            ),
            "expectation_suite_name": "transaction_quality"
        }
    ],
    action_list=[
        {
            "name": "store_validation_result",
            "action": {"class_name": "StoreValidationResultAction"}
        },
        {
            "name": "update_data_docs",
            "action": {"class_name": "UpdateDataDocsAction"}
        },
        {
            "name": "send_slack_notification",
            "action": {
                "class_name": "SlackNotificationAction",
                "slack_webhook": "https://hooks.slack.com/services/...",
                "notify_on": "failure"
            }
        }
    ]
)

# Run in Airflow
results = context.run_checkpoint(checkpoint_name="daily_transaction_validation")

if not results["success"]:
    raise ValueError("Data quality validation failed!")

# Gotcha: Set mostly parameter to allow small % of outliers (prevent false failures)
# Gotcha: Great Expectations HTML reports are large - host on S3 with static website
```

---

### **2. Data Science Track (Week 9-14)**

#### **Week 9-10: EDA & Baseline Models**

**Task 2.1: Exploratory Data Analysis**
```python
# File: ds/notebooks/01_fraud_eda.ipynb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import duckdb

# Fast S3 queries with DuckDB
con = duckdb.connect()
df = con.execute("""
    SELECT * FROM read_parquet('s3://graphguard/transactions/*.parquet')
    WHERE date >= '2024-01-01'
""").df()

# 1. Class Imbalance
fraud_rate = df['fraud'].mean()
print(f"Fraud rate: {fraud_rate:.4f}")  # Typically 0.001-0.01 (0.1-1%)

# Visualization
sns.countplot(data=df, x='fraud')
plt.title(f"Class Distribution (Fraud Rate: {fraud_rate:.2%})")

# 2. Amount Distribution
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
df[df['fraud'] == False]['amount'].hist(bins=50, ax=axes[0], alpha=0.7, label='Legitimate')
df[df['fraud'] == True]['amount'].hist(bins=50, ax=axes[1], alpha=0.7, label='Fraud', color='red')
axes[0].set_title('Legitimate Transaction Amounts')
axes[1].set_title('Fraudulent Transaction Amounts')

# 3. Time Patterns
df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
fraud_by_hour = df.groupby('hour')['fraud'].mean()
fraud_by_hour.plot(kind='bar', title='Fraud Rate by Hour of Day')

# 4. Correlation Matrix
numeric_cols = ['amount', 'txn_count_1h', 'txn_count_24h', 'device_age_days']
correlation = df[numeric_cols + ['fraud']].corr()
sns.heatmap(correlation, annot=True, cmap='coolwarm')

# 5. Outlier Detection
Q1 = df['amount'].quantile(0.25)
Q3 = df['amount'].quantile(0.75)
IQR = Q3 - Q1
outliers = df[(df['amount'] < Q1 - 1.5*IQR) | (df['amount'] > Q3 + 1.5*IQR)]
print(f"Outliers: {len(outliers)} ({len(outliers)/len(df):.2%})")

# 6. Merchant Risk Analysis
merchant_fraud_rate = df.groupby('merchant_id').agg({
    'fraud': ['sum', 'count', 'mean']
}).sort_values(('fraud', 'mean'), ascending=False).head(20)

# Gotcha: Don't use .describe() on full dataset (OOM) - sample first: df.sample(100000).describe()
# Gotcha: Log-transform amount before plotting (most transactions are small)
```

**Task 2.2: Baseline Model - XGBoost**
```python
# File: ds/modeling/baseline_xgboost.py
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve
from imblearn.over_sampling import SMOTE
import mlflow

# Load features from Feast
from feast import FeatureStore
store = FeatureStore(repo_path="feast_repo/")

entity_df = pd.DataFrame({"user_id": df['user_id'], "event_timestamp": df['timestamp']})
features = store.get_historical_features(
    entity_df=entity_df,
    features=[
        "transaction_features:txn_count_1h",
        "transaction_features:txn_count_24h",
        "transaction_features:amount_sum_1h",
        "transaction_features:amount_mean_7d",
        "transaction_features:amount_std_7d",
        "graph_features:pagerank",
        "graph_features:community_id",
        "graph_features:betweenness"
    ]
).to_df()

X = features.drop(columns=['user_id', 'event_timestamp'])
y = df['fraud']

# Train/test split (temporal)
split_date = '2024-06-01'
X_train = X[df['timestamp'] < split_date]
X_test = X[df['timestamp'] >= split_date]
y_train = y[df['timestamp'] < split_date]
y_test = y[df['timestamp'] >= split_date]

# Handle imbalance with SMOTE
smote = SMOTE(sampling_strategy=0.1, random_state=42)  # Upsample minority to 10% of majority
X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)

# Train XGBoost
model = xgb.XGBClassifier(
    max_depth=6,
    learning_rate=0.1,
    n_estimators=200,
    scale_pos_weight=(y_train == 0).sum() / (y_train == 1).sum(),  # Class weight
    subsample=0.8,
    colsample_bytree=0.8,
    gamma=1,
    reg_lambda=10,
    random_state=42,
    eval_metric='aucpr'  # Precision-Recall AUC (better for imbalanced)
)

# Training with early stopping
eval_set = [(X_test, y_test)]
model.fit(
    X_train_balanced, y_train_balanced,
    eval_set=eval_set,
    early_stopping_rounds=20,
    verbose=10
)

# Evaluation
y_pred_proba = model.predict_proba(X_test)[:, 1]
y_pred = (y_pred_proba > 0.5).astype(int)

print(classification_report(y_test, y_pred))
roc_auc = roc_auc_score(y_test, y_pred_proba)
print(f"ROC-AUC: {roc_auc:.4f}")

# Precision-Recall curve (more important than ROC for imbalanced)
precision, recall, thresholds = precision_recall_curve(y_test, y_pred_proba)
plt.plot(recall, precision)
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Curve')

# Log to MLflow
mlflow.set_experiment("fraud_detection")
with mlflow.start_run(run_name="xgboost_baseline"):
    mlflow.log_params({
        "model": "xgboost",
        "max_depth": 6,
        "n_estimators": 200,
        "sampling_strategy": 0.1
    })
    mlflow.log_metrics({
        "roc_auc": roc_auc,
        "precision_at_90_recall": precision[np.argmin(np.abs(recall - 0.9))],
        "recall_at_90_precision": recall[np.argmin(np.abs(precision - 0.9))]
    })
    mlflow.xgboost.log_model(model, "model")
    mlflow.log_artifact("precision_recall_curve.png")

# Feature importance
xgb.plot_importance(model, max_num_features=20)
plt.tight_layout()
plt.savefig("feature_importance.png")
mlflow.log_artifact("feature_importance.png")

# Gotcha: Use scale_pos_weight for class imbalance, not just SMOTE
# Gotcha: eval_metric='aucpr' (Precision-Recall AUC) is better than 'auc' for imbalanced data
# Gotcha: Temporal split (not random) prevents data leakage
```

**Task 2.3: Graph Feature Analysis**
```python
# File: ds/analysis/graph_feature_importance.py
# Goal: Analyze which graph features are most predictive

import shap

# Load trained XGBoost model
model = mlflow.xgboost.load_model("models:/xgboost_fraud/Production")

# Compute SHAP values
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Summary plot
shap.summary_plot(shap_values, X_test, feature_names=X_test.columns)

# Check if graph features are important
graph_feature_importance = {
    'pagerank': np.abs(shap_values[:, X_test.columns.get_loc('pagerank')]).mean(),
    'community_id': np.abs(shap_values[:, X_test.columns.get_loc('community_id')]).mean(),
    'betweenness': np.abs(shap_values[:, X_test.columns.get_loc('betweenness')]).mean()
}

print("Graph Feature Importance (Mean |SHAP|):")
for feature, importance in sorted(graph_feature_importance.items(), key=lambda x: x[1], reverse=True):
    print(f"  {feature}: {importance:.4f}")

# If graph features are top 10: Proceed with GNN
# If graph features are low: Stick with XGBoost on tabular features

# Gotcha: SHAP computation is slow (O(n*m*d)) - sample 1000 instances for large datasets
# Gotcha: TreeExplainer is exact for tree models, KernelExplainer is approximate
```

#### **Week 11-12: Graph Neural Networks**

**Task 2.4: PyTorch Geometric Dataset**
```python
# File: ds/modeling/gnn/dataset.py
# Goal: Create PyG dataset from Neo4j graph

import torch
from torch_geometric.data import Data, Dataset
from neo4j import GraphDatabase
import numpy as np

class FraudGraphDataset(Dataset):
    def __init__(self, neo4j_uri, auth, date_range):
        super().__init__()
        self.driver = GraphDatabase.driver(neo4j_uri, auth=auth)
        self.date_range = date_range
        self.graphs = self._load_graphs()
    
    def _load_graphs(self):
        with self.driver.session() as session:
            # Fetch subgraphs (e.g., 2-hop ego networks around each user)
            result = session.run("""
                MATCH (u:User)
                WHERE u.timestamp >= $start_date AND u.timestamp < $end_date
                CALL gds.alpha.ego(u, 2) YIELD nodes, relationships
                RETURN u.id AS user_id, u.fraud AS label, nodes, relationships
                LIMIT 10000
            """, start_date=self.date_range[0], end_date=self.date_range[1])
            
            graphs = []
            for record in result:
                user_id = record['user_id']
                label = 1 if record['label'] else 0
                nodes = record['nodes']  # List of node IDs
                relationships = record['relationships']  # List of (src, dst, amount)
                
                # Build PyG Data object
                node_features = self._get_node_features(nodes)
                edge_index = self._get_edge_index(relationships)
                edge_attr = self._get_edge_features(relationships)
                
                data = Data(
                    x=node_features,
                    edge_index=edge_index,
                    edge_attr=edge_attr,
                    y=torch.tensor([label], dtype=torch.long),
                    user_id=user_id
                )
                graphs.append(data)
            
            return graphs
    
    def _get_node_features(self, nodes):
        # Query Neo4j for node properties (pagerank, degree, etc.)
        with self.driver.session() as session:
            result = session.run("""
                UNWIND $nodes AS node_id
                MATCH (n) WHERE ID(n) = node_id
                RETURN n.pagerank AS pagerank, 
                       n.betweenness AS betweenness,
                       SIZE((n)-[:TRANSACTED_WITH]->()) AS out_degree
            """, nodes=nodes)
            
            features = []
            for record in result:
                features.append([
                    record['pagerank'] or 0,
                    record['betweenness'] or 0,
                    record['out_degree'] or 0
                ])
            
            return torch.tensor(features, dtype=torch.float)
    
    def _get_edge_index(self, relationships):
        # Convert Neo4j relationships to PyG edge_index
        edges = [(rel[0], rel[1]) for rel in relationships]
        edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
        return edge_index
    
    def _get_edge_features(self, relationships):
        # Transaction amounts as edge features
        amounts = [rel[2] for rel in relationships]
        return torch.tensor(amounts, dtype=torch.float).unsqueeze(1)
    
    def len(self):
        return len(self.graphs)
    
    def get(self, idx):
        return self.graphs[idx]

# Usage
dataset = FraudGraphDataset(
    neo4j_uri="bolt://neo4j:7687",
    auth=("neo4j", "password"),
    date_range=("2024-01-01", "2024-06-01")
)

# Gotcha: Neo4j queries are slow - cache subgraphs to disk with torch.save(dataset, 'dataset.pt')
# Gotcha: ego() function requires GDS library installed in Neo4j
```

**Task 2.5: Graph Attention Network (GAT)**
```python
# File: ds/modeling/gnn/gat_model.py
import torch
import torch.nn.functional as F
from torch_geometric.nn import GATConv, global_mean_pool
from torch_geometric.loader import DataLoader

class FraudGAT(torch.nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels, heads=8):
        super().__init__()
        self.conv1 = GATConv(in_channels, hidden_channels, heads=heads, dropout=0.6)
        self.conv2 = GATConv(hidden_channels * heads, hidden_channels, heads=1, concat=False, dropout=0.6)
        self.fc1 = torch.nn.Linear(hidden_channels, hidden_channels // 2)
        self.fc2 = torch.nn.Linear(hidden_channels // 2, out_channels)
    
    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch
        
        # GAT layers
        x = F.dropout(x, p=0.6, training=self.training)
        x = F.elu(self.conv1(x, edge_index))
        x = F.dropout(x, p=0.6, training=self.training)
        x = self.conv2(x, edge_index)
        
        # Graph-level pooling
        x = global_mean_pool(x, batch)
        
        # MLP classifier
        x = F.relu(self.fc1(x))
        x = F.dropout(x, p=0.5, training=self.training)
        x = self.fc2(x)
        
        return F.log_softmax(x, dim=1)

# Training
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = FraudGAT(in_channels=3, hidden_channels=128, out_channels=2).to(device)
optimizer = torch.optim.Adam(model.parameters(), lr=0.005, weight_decay=5e-4)

train_loader = DataLoader(dataset[:8000], batch_size=32, shuffle=True)
test_loader = DataLoader(dataset[8000:], batch_size=32)

def train():
    model.train()
    total_loss = 0
    for data in train_loader:
        data = data.to(device)
        optimizer.zero_grad()
        out = model(data)
        loss = F.nll_loss(out, data.y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / len(train_loader)

def test():
    model.eval()
    correct = 0
    for data in test_loader:
        data = data.to(device)
        pred = model(data).argmax(dim=1)
        correct += (pred == data.y).sum().item()
    return correct / len(test_loader.dataset)

for epoch in range(1, 201):
    loss = train()
    if epoch % 10 == 0:
        acc = test()
        print(f'Epoch: {epoch:03d}, Loss: {loss:.4f}, Test Acc: {acc:.4f}')

# Save model
torch.save(model.state_dict(), 'gat_fraud_detector.pth')
mlflow.pytorch.log_model(model, "gat_model")

# Gotcha: GAT needs entire graph in memory - use NeighborLoader for large graphs (>1M nodes)
# Gotcha: Multi-head attention (heads=8) improves performance but increases memory
```

**Task 2.6: Ensemble Model**
```python
# File: ds/modeling/ensemble.py
# Goal: Combine XGBoost (tabular) + GAT (graph) predictions

import torch
import xgboost as xgb
from scipy.special import softmax

# Load models
xgb_model = mlflow.xgboost.load_model("models:/xgboost_fraud/Production")
gat_model = FraudGAT(in_channels=3, hidden_channels=128, out_channels=2)
gat_model.load_state_dict(torch.load('gat_fraud_detector.pth'))
gat_model.eval()

def ensemble_predict(user_id, transaction_features, graph_data):
    # XGBoost prediction (tabular features)
    xgb_proba = xgb_model.predict_proba([transaction_features])[0, 1]
    
    # GAT prediction (graph features)
    with torch.no_grad():
        gat_out = gat_model(graph_data)
        gat_proba = torch.exp(gat_out)[0, 1].item()
    
    # Ensemble: Weighted average
    ensemble_proba = 0.6 * xgb_proba + 0.4 * gat_proba
    
    return ensemble_proba

# Evaluate ensemble
test_predictions = []
test_labels = []

for i, data in enumerate(test_loader):
    user_id = data.user_id[0]
    transaction_features = X_test.iloc[i].values
    graph_data = data.to(device)
    
    proba = ensemble_predict(user_id, transaction_features, graph_data)
    test_predictions.append(proba)
    test_labels.append(data.y.item())

# Metrics
from sklearn.metrics import roc_auc_score, precision_recall_fscore_support
auc = roc_auc_score(test_labels, test_predictions)
pred_binary = [1 if p > 0.5 else 0 for p in test_predictions]
precision, recall, f1, _ = precision_recall_fscore_support(test_labels, pred_binary, average='binary')

print(f"Ensemble AUC: {auc:.4f}")
print(f"Ensemble Precision: {precision:.4f}, Recall: {recall:.4f}, F1: {f1:.4f}")

# Compare to baselines
print(f"XGBoost alone: AUC={xgb_auc:.4f}, F1={xgb_f1:.4f}")
print(f"GAT alone: AUC={gat_auc:.4f}, F1={gat_f1:.4f}")
print(f"Ensemble: AUC={auc:.4f}, F1={f1:.4f}")

# Gotcha: Ensemble weights (0.6, 0.4) should be tuned via cross-validation
# Gotcha: If GAT doesn't improve over XGBoost, stick with XGBoost (simpler)
```

#### **Week 13-14: Explainability & Model Analysis**

**Task 2.7: SHAP for Ensemble Model**
```python
# File: ds/explainability/shap_analysis.py
import shap
import numpy as np

# Wrapper for ensemble model
def ensemble_predict_wrapper(X):
    predictions = []
    for i, features in enumerate(X):
        # For SHAP, we need graph data - use cached subgraph
        graph_data = cached_graphs[i]
        pred = ensemble_predict(None, features, graph_data)
        predictions.append([1 - pred, pred])  # [prob_class_0, prob_class_1]
    return np.array(predictions)

# SHAP explainer (TreeExplainer for XGBoost component)
xgb_explainer = shap.TreeExplainer(xgb_model)
xgb_shap_values = xgb_explainer.shap_values(X_test)

# For GAT, use KernelExplainer (model-agnostic, slower)
gat_explainer = shap.KernelExplainer(
    lambda x: ensemble_predict_wrapper(x),
    shap.sample(X_train, 100)  # Background dataset
)
gat_shap_values = gat_explainer.shap_values(X_test[:100])  # Sample 100 due to slowness

# Visualizations
shap.summary_plot(xgb_shap_values, X_test, feature_names=X_test.columns)
shap.waterfall_plot(shap.Explanation(
    values=xgb_shap_values[0],
    base_values=xgb_explainer.expected_value,
    data=X_test.iloc[0],
    feature_names=X_test.columns
))

# Store SHAP values for API
import joblib
joblib.dump({
    'explainer': xgb_explainer,
    'expected_value': xgb_explainer.expected_value
}, 'shap_explainer.pkl')

# Gotcha: KernelExplainer is O(n^2 * m) - very slow, use TreeExplainer when possible
# Gotcha: Cache SHAP values for frequently queried users (Redis)
```

**Task 2.8: Graph Visualization for Investigators**
```python
# File: ds/explainability/graph_visualization.py
# Goal: Generate D3.js-compatible JSON for suspicious subgraphs

from neo4j import GraphDatabase
import json

def extract_suspicious_subgraph(user_id, threshold=0.7):
    """
    Extract subgraph around a high-risk user for investigation
    """
    driver = GraphDatabase.driver("bolt://neo4j:7687")
    
    with driver.session() as session:
        # Find users in same community with high fraud rate
        result = session.run("""
            MATCH (u:User {id: $user_id})
            MATCH (u)-[:IN_COMMUNITY]->(c:Community)
            MATCH (c)<-[:IN_COMMUNITY]-(other:User)
            WHERE other.fraud = true OR other.predicted_fraud_score > $threshold
            
            MATCH path = (u)-[:TRANSACTED_WITH*1..2]-(other)
            RETURN u, other, relationships(path) AS edges
            LIMIT 50
        """, user_id=user_id, threshold=threshold)
        
        nodes = {}
        edges = []
        
        for record in result:
            # Add nodes
            for user in [record['u'], record['other']]:
                user_id = user['id']
                if user_id not in nodes:
                    nodes[user_id] = {
                        'id': user_id,
                        'fraud': user.get('fraud', False),
                        'predicted_score': user.get('predicted_fraud_score', 0),
                        'pagerank': user.get('pagerank', 0)
                    }
            
            # Add edges
            for edge in record['edges']:
                edges.append({
                    'source': edge.start_node['id'],
                    'target': edge.end_node['id'],
                    'amount': edge['amount'],
                    'timestamp': edge['timestamp']
                })
        
        # Convert to D3.js format
        graph_data = {
            'nodes': list(nodes.values()),
            'edges': edges
        }
        
        return graph_data

# Example usage
subgraph = extract_suspicious_subgraph(user_id="user_12345")
with open('suspicious_subgraph.json', 'w') as f:
    json.dump(subgraph, f)

# Gotcha: Large subgraphs (>100 nodes) crash D3.js - limit query results
# Gotcha: Include edge directionality for better visualization
```

---

### **3. ML Engineering Track (Week 15-20)**

#### **Week 15-16: Model Serving**

**Task 3.1: FastAPI Inference Endpoint**
```python
# File: ml/serving/api.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import torch
import xgboost as xgb
from feast import FeatureStore
import redis
import json

app = FastAPI(title="GraphGuard Fraud Detection API", version="2.0.0")

# Load models
xgb_model = xgb.Booster()
xgb_model.load_model('models/xgboost_fraud.bin')

gat_model = FraudGAT(in_channels=3, hidden_channels=128, out_channels=2)
gat_model.load_state_dict(torch.load('models/gat_fraud.pth'))
gat_model.eval()

# Feast feature store
feast_store = FeatureStore(repo_path="feast_repo/")

# Redis cache
redis_client = redis.Redis(host='redis', port=6379, decode_responses=True)

class TransactionRequest(BaseModel):
    transaction_id: str
    user_id: str
    merchant_id: str
    amount: float
    currency: str
    device_id: str
    ip_address: str

class PredictionResponse(BaseModel):
    transaction_id: str
    fraud_score: float
    decision: str  # AUTO_APPROVE, REVIEW, AUTO_DECLINE
    latency_ms: int
    model_version: str
    explanation: dict

@app.post("/score", response_model=PredictionResponse)
async def score_transaction(request: TransactionRequest):
    import time
    start_time = time.time()
    
    # 1. Check cache (15% of requests are repeat users)
    cache_key = f"fraud_score:{request.user_id}:{request.merchant_id}"
    cached_score = redis_client.get(cache_key)
    if cached_score:
        return PredictionResponse(
            transaction_id=request.transaction_id,
            fraud_score=float(cached_score),
            decision="REVIEW",
            latency_ms=int((time.time() - start_time) * 1000),
            model_version="cached",
            explanation={}
        )
    
    # 2. Fetch features from Feast
    features = feast_store.get_online_features(
        entity_rows=[{"user_id": request.user_id, "merchant_id": request.merchant_id}],
        features=[
            "transaction_features:txn_count_1h",
            "transaction_features:txn_count_24h",
            "transaction_features:amount_sum_1h",
            "graph_features:pagerank",
            "graph_features:community_id"
        ]
    ).to_dict()
    
    feature_vector = [
        features['txn_count_1h'][0],
        features['txn_count_24h'][0],
        features['amount_sum_1h'][0],
        features['pagerank'][0],
        features['community_id'][0],
        request.amount,  # Real-time feature
    ]
    
    # 3. XGBoost prediction
    import xgboost as xgb
    dmatrix = xgb.DMatrix([feature_vector])
    xgb_score = xgb_model.predict(dmatrix)[0]
    
    # 4. GAT prediction (fetch subgraph from Neo4j)
    # TODO: Implement graph fetching + GAT inference
    gat_score = 0.5  # Placeholder
    
    # 5. Ensemble
    fraud_score = 0.6 * xgb_score + 0.4 * gat_score
    
    # 6. Decision logic
    if fraud_score < 0.3:
        decision = "AUTO_APPROVE"
    elif fraud_score < 0.7:
        decision = "REVIEW"
    else:
        decision = "AUTO_DECLINE"
    
    # 7. Cache result (TTL: 15 minutes)
    redis_client.setex(cache_key, 900, fraud_score)
    
    # 8. Generate explanation
    explanation = {
        "top_features": [
            {"feature": "txn_count_1h", "value": features['txn_count_1h'][0], "importance": 0.3},
            {"feature": "amount", "value": request.amount, "importance": 0.25}
        ],
        "graph_reasoning": f"User pagerank: {features['pagerank'][0]:.4f}"
    }
    
    latency_ms = int((time.time() - start_time) * 1000)
    
    # 9. Audit log (async publish to Kafka)
    await publish_audit_log(request, fraud_score, decision)
    
    return PredictionResponse(
        transaction_id=request.transaction_id,
        fraud_score=fraud_score,
        decision=decision,
        latency_ms=latency_ms,
        model_version="ensemble_v2",
        explanation=explanation
    )

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": xgb_model is not None}

# Gotcha: Use async def for I/O-bound operations (Feast, Neo4j)
# Gotcha: Set Uvicorn workers=4 for parallelism
```

**Task 3.2: Feature Caching Strategy**
```python
# File: ml/serving/feature_cache.py
import redis
import json
from typing import Dict, List
import hashlib

class FeatureCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 900  # 15 minutes
    
    def get_features(self, user_id: str, feature_names: List[str]) -> Dict:
        """
        Get cached features or fetch from Feast
        """
        cache_key = self._cache_key(user_id, feature_names)
        cached = self.redis.get(cache_key)
        
        if cached:
            return json.loads(cached)
        
        # Fetch from Feast
        from feast import FeatureStore
        store = FeatureStore(repo_path="feast_repo/")
        features = store.get_online_features(
            entity_rows=[{"user_id": user_id}],
            features=feature_names
        ).to_dict()
        
        # Cache
        self.redis.setex(cache_key, self.ttl, json.dumps(features))
        return features
    
    def _cache_key(self, user_id: str, feature_names: List[str]) -> str:
        # Deterministic key
        feature_str = ",".join(sorted(feature_names))
        return f"features:{user_id}:{hashlib.md5(feature_str.encode()).hexdigest()[:8]}"


        # Invalidate cache
    def invalidate_user(self, user_id: str):
        """Invalidate all cached features for a user"""
        pattern = f"features:{user_id}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)

# Usage in API
feature_cache = FeatureCache(redis_client)

@app.post("/score")
async def score_transaction(request: TransactionRequest):
    features = feature_cache.get_features(
        user_id=request.user_id,
        feature_names=["transaction_features:txn_count_1h", ...]
    )
    # ... rest of scoring logic

# Gotcha: Cache key includes feature_names hash to avoid stale data when feature set changes
# Gotcha: Implement cache warming for high-value users (VIPs)
```

**Task 3.3: Model Versioning & A/B Testing**
```python
# File: ml/serving/model_router.py
from enum import Enum
import random

class ModelVersion(Enum):
    CHAMPION = "ensemble_v2"
    CHALLENGER = "ensemble_v3_gat_improved"

class ModelRouter:
    def __init__(self):
        self.champion_weight = 0.9  # 90% traffic
        self.challenger_weight = 0.1  # 10% traffic
        
        # Load both models
        self.champion_model = self._load_model(ModelVersion.CHAMPION)
        self.challenger_model = self._load_model(ModelVersion.CHALLENGER)
    
    def _load_model(self, version: ModelVersion):
        # Load from MLflow registry
        import mlflow
        model_uri = f"models:/fraud_ensemble/{version.value}"
        return mlflow.pyfunc.load_model(model_uri)
    
    def route_request(self, request: TransactionRequest):
        """Route request to champion or challenger"""
        if random.random() < self.challenger_weight:
            return self.challenger_model, ModelVersion.CHALLENGER
        else:
            return self.champion_model, ModelVersion.CHAMPION
    
    def predict(self, request: TransactionRequest):
        model, version = self.route_request(request)
        
        # Make prediction
        features = self._extract_features(request)
        prediction = model.predict(features)
        
        # Log for A/B analysis
        self._log_prediction(request.transaction_id, version, prediction)
        
        return prediction, version
    
    def _log_prediction(self, txn_id, version, prediction):
        # Log to Kafka for later analysis
        kafka_producer.send('model.predictions', {
            'transaction_id': txn_id,
            'model_version': version.value,
            'prediction': prediction,
            'timestamp': datetime.utcnow().isoformat()
        })

router = ModelRouter()

@app.post("/score")
async def score_transaction(request: TransactionRequest):
    prediction, model_version = router.predict(request)
    # ...

# Gotcha: Use consistent hashing (user_id) instead of random() to ensure same user always gets same model
# Gotcha: Log BOTH champion and challenger predictions for unbiased comparison
```

#### **Week 17-18: Model Monitoring & Retraining**

**Task 3.4: Evidently AI Drift Detection**
```python
# File: ml/monitoring/drift_detection.py
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset, TargetDriftPreset
from evidently.metrics import *
import pandas as pd

def detect_drift(reference_data: pd.DataFrame, current_data: pd.DataFrame):
    """
    Detect data drift and model drift
    """
    # Define column types
    column_mapping = ColumnMapping(
        target='fraud',
        prediction='prediction',
        numerical_features=['amount', 'txn_count_1h', 'txn_count_24h', 'pagerank'],
        categorical_features=['currency', 'merchant_id']
    )
    
    # Create drift report
    report = Report(metrics=[
        DataDriftPreset(),
        DataQualityPreset(),
        TargetDriftPreset(),
        ClassificationQualityMetric(),
        ClassificationClassBalance(),
    ])
    
    report.run(
        reference_data=reference_data,
        current_data=current_data,
        column_mapping=column_mapping
    )
    
    # Extract key metrics
    report_dict = report.as_dict()
    
    data_drift_detected = report_dict['metrics'][0]['result']['dataset_drift']
    drift_score = report_dict['metrics'][0]['result']['drift_score']
    drifted_features = [
        feature for feature, result in report_dict['metrics'][0]['result']['drift_by_columns'].items()
        if result['drift_detected']
    ]
    
    # Save report
    report.save_html('reports/drift_report.html')
    
    # Alert if drift detected
    if data_drift_detected:
        send_slack_alert(
            f"🚨 Data Drift Detected! Score: {drift_score:.3f}\n"
            f"Drifted features: {', '.join(drifted_features)}"
        )
        
        # Trigger retraining
        trigger_airflow_dag('model_retraining_pipeline')
    
    return {
        'drift_detected': data_drift_detected,
        'drift_score': drift_score,
        'drifted_features': drifted_features
    }

# Run daily via Airflow
def daily_drift_check():
    # Load reference data (training set)
    reference_data = pd.read_parquet('s3://graphguard/training/reference_dataset.parquet')
    
    # Load current production data (last 24h)
    current_data = pd.read_parquet(f's3://graphguard/logs/predictions/{date.today()}.parquet')
    
    detect_drift(reference_data, current_data)

# Gotcha: Reference data should be recent (within 3 months) - old reference causes false alarms
# Gotcha: High-cardinality features (user_id, merchant_id) will always drift - exclude from drift detection
```

**Task 3.5: Model Performance Monitoring**
```python
# File: ml/monitoring/performance_monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Prometheus metrics
prediction_counter = Counter('fraud_predictions_total', 'Total predictions', ['model_version', 'decision'])
prediction_latency = Histogram('fraud_prediction_latency_seconds', 'Prediction latency', ['model_version'])
fraud_rate_gauge = Gauge('fraud_rate', 'Current fraud rate')
cache_hit_rate = Gauge('feature_cache_hit_rate', 'Feature cache hit rate')

class PerformanceMonitor:
    def __init__(self):
        self.window_size = 1000
        self.predictions = []
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_prediction(self, model_version: str, decision: str, latency: float, fraud_score: float):
        # Prometheus metrics
        prediction_counter.labels(model_version=model_version, decision=decision).inc()
        prediction_latency.labels(model_version=model_version).observe(latency)
        
        # Track fraud rate
        self.predictions.append(fraud_score)
        if len(self.predictions) > self.window_size:
            self.predictions.pop(0)
        
        fraud_rate = sum(1 for p in self.predictions if p > 0.5) / len(self.predictions)
        fraud_rate_gauge.set(fraud_rate)
    
    def record_cache_event(self, hit: bool):
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        total = self.cache_hits + self.cache_misses
        cache_hit_rate.set(self.cache_hits / total if total > 0 else 0)

monitor = PerformanceMonitor()

# In scoring endpoint
@app.post("/score")
async def score_transaction(request: TransactionRequest):
    start_time = time.time()
    
    # ... scoring logic ...
    
    latency = time.time() - start_time
    monitor.record_prediction(model_version, decision, latency, fraud_score)
    
    return response

# Grafana dashboard query:
# rate(fraud_predictions_total[5m])  # Predictions per second
# histogram_quantile(0.99, fraud_prediction_latency_seconds)  # P99 latency
# fraud_rate  # Current fraud rate

# Gotcha: Use histograms for latency (not averages) - need percentiles (p50, p95, p99)
# Gotcha: Set up alerts: P99 latency > 200ms, fraud rate > 5%
```

**Task 3.6: Automated Retraining Pipeline**
```python
# File: airflow/dags/model_retraining_pipeline.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.operators.emr import EmrAddStepsOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'ml-eng',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': True,
    'email': ['ml-team@graphguard.com'],
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

def check_retraining_criteria():
    """
    Decide if retraining is needed
    """
    # Criteria 1: New labels (>1000 since last training)
    new_labels_count = count_new_labels_since_last_training()
    
    # Criteria 2: Model performance degraded (precision < 0.85)
    current_performance = get_current_model_performance()
    
    # Criteria 3: Data drift detected
    drift_detected = check_latest_drift_report()
    
    if new_labels_count > 1000 or current_performance['precision'] < 0.85 or drift_detected:
        return True
    else:
        raise AirflowSkipException("Retraining criteria not met")

def train_new_model():
    """
    Train XGBoost + GAT ensemble
    """
    import ray
    from ray import tune
    
    # Connect to Ray cluster
    ray.init(address="ray://ray-head:10001")
    
    # Load data
    X_train, y_train = load_training_data()
    X_test, y_test = load_test_data()
    
    # Hyperparameter tuning with Ray Tune
    config = {
        "xgb_max_depth": tune.randint(3, 10),
        "xgb_learning_rate": tune.loguniform(0.001, 0.1),
        "gat_hidden_channels": tune.choice([64, 128, 256]),
        "gat_heads": tune.choice([4, 8, 16])
    }
    
    analysis = tune.run(
        train_ensemble,
        config=config,
        num_samples=50,
        resources_per_trial={"cpu": 4, "gpu": 1}
    )
    
    best_config = analysis.get_best_config(metric="f1", mode="max")
    
    # Train final model with best config
    model = train_ensemble(best_config)
    
    # Save to MLflow
    with mlflow.start_run(run_name=f"retrain_{datetime.now().isoformat()}"):
        mlflow.log_params(best_config)
        mlflow.log_metrics({"f1": analysis.best_result["f1"]})
        mlflow.sklearn.log_model(model, "model")
        
        # Tag as challenger
        mlflow.set_tag("stage", "challenger")

def evaluate_new_model():
    """
    Evaluate new model vs current production model
    """
    challenger_model = mlflow.sklearn.load_model("runs:/<latest_run_id>/model")
    champion_model = mlflow.sklearn.load_model("models:/fraud_ensemble/Production")
    
    X_test, y_test = load_test_data()
    
    challenger_metrics = evaluate_model(challenger_model, X_test, y_test)
    champion_metrics = evaluate_model(champion_model, X_test, y_test)
    
    # Statistical test: paired t-test on F1 scores
    from scipy import stats
    t_stat, p_value = stats.ttest_rel(challenger_metrics['f1_per_fold'], champion_metrics['f1_per_fold'])
    
    if p_value < 0.05 and challenger_metrics['f1'] > champion_metrics['f1']:
        # Challenger is significantly better
        promote_to_production = True
    else:
        promote_to_production = False
    
    # Store decision
    with open('/tmp/promote_decision.txt', 'w') as f:
        f.write(str(promote_to_production))
    
    return promote_to_production

def deploy_new_model():
    """
    Promote challenger to production
    """
    # Read decision
    with open('/tmp/promote_decision.txt', 'r') as f:
        promote = f.read() == 'True'
    
    if not promote:
        send_slack_alert("New model did not outperform champion. Keeping current model.")
        return
    
    # Promote in MLflow
    from mlflow.tracking import MlflowClient
    client = MlflowClient()
    
    latest_version = client.get_latest_versions("fraud_ensemble", stages=["None"])[0]
    client.transition_model_version_stage(
        name="fraud_ensemble",
        version=latest_version.version,
        stage="Production",
        archive_existing_versions=True
    )
    
    # Update FastAPI to load new model (rolling update)
    os.system("kubectl rollout restart deployment/fraud-api")
    
    send_slack_alert(f"🎉 New model v{latest_version.version} deployed to production!")

with DAG(
    'model_retraining_pipeline',
    default_args=default_args,
    schedule_interval='@weekly',
    catchup=False
) as dag:
    
    check_criteria = PythonOperator(
        task_id='check_retraining_criteria',
        python_callable=check_retraining_criteria
    )
    
    train = PythonOperator(
        task_id='train_new_model',
        python_callable=train_new_model
    )
    
    evaluate = PythonOperator(
        task_id='evaluate_new_model',
        python_callable=evaluate_new_model
    )
    
    deploy = PythonOperator(
        task_id='deploy_new_model',
        python_callable=deploy_new_model
    )
    
    check_criteria >> train >> evaluate >> deploy

# Gotcha: Use @weekly schedule, not @daily - retraining too often wastes compute
# Gotcha: Always compare new model to production baseline with statistical tests
# Gotcha: Keep champion model as fallback (canary deployment: 10% challenger, 90% champion)
```

#### **Week 19-20: Production Deployment & A/B Testing**

**Task 3.7: Canary Deployment**
```yaml
# File: k8s/fraud-api-canary.yaml
apiVersion: v1
kind: Service
metadata:
  name: fraud-api
spec:
  selector:
    app: fraud-api
  ports:
  - port: 80
    targetPort: 8000

---
# Champion deployment (90% traffic)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fraud-api-champion
spec:
  replicas: 9
  selector:
    matchLabels:
      app: fraud-api
      version: champion
  template:
    metadata:
      labels:
        app: fraud-api
        version: champion
    spec:
      containers:
      - name: api
        image: graphguard/fraud-api:v2.3.1
        env:
        - name: MODEL_VERSION
          value: "champion"
        resources:
          requests:
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# Challenger deployment (10% traffic)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fraud-api-challenger
spec:
  replicas: 1
  selector:
    matchLabels:
      app: fraud-api
      version: challenger
  template:
    metadata:
      labels:
        app: fraud-api
        version: challenger
    spec:
      containers:
      - name: api
        image: graphguard/fraud-api:v2.4.0-rc
        env:
        - name: MODEL_VERSION
          value: "challenger"
        resources:
          requests:
            cpu: "1000m"
            memory: "2Gi"

# Gotcha: Use Service weight via Istio VirtualService for precise traffic splitting
# Gotcha: Set readinessProbe to prevent routing to unhealthy pods during rollout
```

**Task 3.8: A/B Test Analysis**
```python
# File: ml/experimentation/ab_test_analysis.py
import pandas as pd
from scipy import stats
import matplotlib.pyplot as plt

def analyze_ab_test(start_date: str, end_date: str):
    """
    Analyze A/B test results between champion and challenger
    """
    # Load predictions from Kafka logs
    df = pd.read_parquet(f's3://graphguard/logs/predictions/{start_date}_to_{end_date}.parquet')
    
    champion_df = df[df['model_version'] == 'champion']
    challenger_df = df[df['model_version'] == 'challenger']
    
    print(f"Champion samples: {len(champion_df)}")
    print(f"Challenger samples: {len(challenger_df)}")
    
    # Metrics
    metrics = {}
    
    # 1. Precision at 90% recall
    from sklearn.metrics import precision_recall_curve
    
    champion_precision, champion_recall, _ = precision_recall_curve(
        champion_df['true_label'], champion_df['prediction']
    )
    champion_p90r = champion_precision[np.argmin(np.abs(champion_recall - 0.9))]
    
    challenger_precision, challenger_recall, _ = precision_recall_curve(
        challenger_df['true_label'], challenger_df['prediction']
    )
    challenger_p90r = challenger_precision[np.argmin(np.abs(challenger_recall - 0.9))]
    
    metrics['precision_at_90_recall'] = {
        'champion': champion_p90r,
        'challenger': challenger_p90r,
        'improvement': (challenger_p90r - champion_p90r) / champion_p90r
    }
    
    # 2. ROC-AUC
    from sklearn.metrics import roc_auc_score
    champion_auc = roc_auc_score(champion_df['true_label'], champion_df['prediction'])
    challenger_auc = roc_auc_score(challenger_df['true_label'], challenger_df['prediction'])
    
    metrics['roc_auc'] = {
        'champion': champion_auc,
        'challenger': challenger_auc,
        'improvement': (challenger_auc - champion_auc) / champion_auc
    }
    
    # 3. False Positive Rate at 95% recall
    champion_fpr = calculate_fpr_at_recall(champion_df, recall_threshold=0.95)
    challenger_fpr = calculate_fpr_at_recall(challenger_df, recall_threshold=0.95)
    
    metrics['fpr_at_95_recall'] = {
        'champion': champion_fpr,
        'challenger': challenger_fpr,
        'improvement': (champion_fpr - challenger_fpr) / champion_fpr  # Lower is better
    }
    
    # 4. Latency
    champion_latency = champion_df['latency_ms'].quantile(0.99)
    challenger_latency = challenger_df['latency_ms'].quantile(0.99)
    
    metrics['p99_latency_ms'] = {
        'champion': champion_latency,
        'challenger': challenger_latency,
        'improvement': (champion_latency - challenger_latency) / champion_latency
    }
    
    # Statistical test: Paired t-test on daily metrics
    champion_daily_f1 = champion_df.groupby('date').apply(lambda x: f1_score(x['true_label'], x['prediction'] > 0.5))
    challenger_daily_f1 = challenger_df.groupby('date').apply(lambda x: f1_score(x['true_label'], x['prediction'] > 0.5))
    
    t_stat, p_value = stats.ttest_rel(challenger_daily_f1, champion_daily_f1)
    
    # Decision
    if p_value < 0.05 and metrics['roc_auc']['improvement'] > 0.02:  # 2% improvement threshold
        decision = "PROMOTE_CHALLENGER"
        confidence = 1 - p_value
    else:
        decision = "KEEP_CHAMPION"
        confidence = p_value
    
    # Generate report
    report = f"""
    A/B Test Results ({start_date} to {end_date})
    ============================================
    
    Samples:
    - Champion: {len(champion_df):,}
    - Challenger: {len(challenger_df):,}
    
    Metrics:
    - Precision@90%Recall: Champion={champion_p90r:.3f}, Challenger={challenger_p90r:.3f} ({metrics['precision_at_90_recall']['improvement']:.1%})
    - ROC-AUC: Champion={champion_auc:.3f}, Challenger={challenger_auc:.3f} ({metrics['roc_auc']['improvement']:.1%})
    - FPR@95%Recall: Champion={champion_fpr:.3f}, Challenger={challenger_fpr:.3f} ({metrics['fpr_at_95_recall']['improvement']:.1%})
    - P99 Latency: Champion={champion_latency:.0f}ms, Challenger={challenger_latency:.0f}ms ({metrics['p99_latency_ms']['improvement']:.1%})
    
    Statistical Test:
    - t-statistic: {t_stat:.3f}
    - p-value: {p_value:.4f}
    
    Decision: {decision} (confidence: {confidence:.1%})
    """
    
    print(report)
    
    # Visualizations
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    # Precision-Recall curves
    axes[0, 0].plot(champion_recall, champion_precision, label='Champion', color='blue')
    axes[0, 0].plot(challenger_recall, challenger_precision, label='Challenger', color='red')
    axes[0, 0].set_xlabel('Recall')
    axes[0, 0].set_ylabel('Precision')
    axes[0, 0].legend()
    axes[0, 0].set_title('Precision-Recall Curve')
    
    # ROC curves
    from sklearn.metrics import roc_curve
    champion_fpr, champion_tpr, _ = roc_curve(champion_df['true_label'], champion_df['prediction'])
    challenger_fpr, challenger_tpr, _ = roc_curve(challenger_df['true_label'], challenger_df['prediction'])
    axes[0, 1].plot(champion_fpr, champion_tpr, label=f'Champion (AUC={champion_auc:.3f})', color='blue')
    axes[0, 1].plot(challenger_fpr, challenger_tpr, label=f'Challenger (AUC={challenger_auc:.3f})', color='red')
    axes[0, 1].set_xlabel('False Positive Rate')
    axes[0, 1].set_ylabel('True Positive Rate')
    axes[0, 1].legend()
    axes[0, 1].set_title('ROC Curve')
    
    # Latency distribution
    axes[1, 0].hist(champion_df['latency_ms'], bins=50, alpha=0.5, label='Champion', color='blue')
    axes[1, 0].hist(challenger_df['latency_ms'], bins=50, alpha=0.5, label='Challenger', color='red')
    axes[1, 0].set_xlabel('Latency (ms)')
    axes[1, 0].set_ylabel('Count')
    axes[1, 0].legend()
    axes[1, 0].set_title('Latency Distribution')
    
    # Daily F1 score
    axes[1, 1].plot(champion_daily_f1.index, champion_daily_f1.values, marker='o', label='Champion', color='blue')
    axes[1, 1].plot(challenger_daily_f1.index, challenger_daily_f1.values, marker='o', label='Challenger', color='red')
    axes[1, 1].set_xlabel('Date')
    axes[1, 1].set_ylabel('F1 Score')
    axes[1, 1].legend()
    axes[1, 1].set_title('Daily F1 Score')
    
    plt.tight_layout()
    plt.savefig('ab_test_results.png')
    
    # Send to Slack
    send_slack_alert(report, attachment='ab_test_results.png')
    
    return decision, metrics

# Run weekly
if __name__ == "__main__":
    decision, metrics = analyze_ab_test(
        start_date=(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        end_date=datetime.now().strftime('%Y-%m-%d')
    )

# Gotcha: Need at least 1000 samples per variant for statistical power
# Gotcha: Use stratified sampling if fraud rate varies by day of week
```

---

### **4. Full-Stack Engineering Track (Week 21-26)**

#### **Week 21-22: Backend API (GraphQL)**

**Task 4.1: GraphQL Schema Design**
```graphql
# File: backend/schema.graphql

type Query {
  """Get fraud case details"""
  fraudCase(id: ID!): FraudCase
  
  """Get fraud queue for investigator"""
  fraudQueue(
    status: FraudStatus
    limit: Int = 50
    offset: Int = 0
  ): FraudQueueConnection!
  
  """Get transaction details"""
  transaction(id: ID!): Transaction
  
  """Get user transaction history"""
  userTransactions(
    userId: ID!
    limit: Int = 100
    startDate: DateTime
    endDate: DateTime
  ): [Transaction!]!
  
  """Get suspicious subgraph around a user"""
  suspiciousSubgraph(userId: ID!, hops: Int = 2): TransactionGraph!
  
  """Get SHAP explanation for a prediction"""
  shapExplanation(transactionId: ID!): ShapExplanation!
  
  """Search fraud cases"""
  searchCases(query: String!, limit: Int = 20): [FraudCase!]!
}

type Mutation {
  """Label a fraud case"""
  labelCase(id: ID!, label: FraudLabel!, notes: String): FraudCase!
  
  """Escalate a case"""
  escalateCase(id: ID!, reason: String!): FraudCase!
  
  """Block a user"""
  blockUser(userId: ID!, reason: String!): User!
  
  """Whitelist a merchant"""
  whitelistMerchant(merchantId: ID!): Merchant!
}

type Subscription {
  """Real-time updates for fraud queue"""
  fraudQueueUpdated(investigatorId: ID!): FraudCase!
}

type FraudCase {
  id: ID!
  transaction: Transaction!
  fraudScore: Float!
  status: FraudStatus!
  assignedTo: Investigator
  createdAt: DateTime!
  updatedAt: DateTime!
  notes: [CaseNote!]!
  evidence: Evidence!
}

enum FraudStatus {
  PENDING
  IN_REVIEW
  RESOLVED_FRAUD
  RESOLVED_LEGITIMATE
  ESCALATED
}

type Transaction {
  id: ID!
  user: User!
  merchant: Merchant!
  amount: Float!
  currency: String!
  timestamp: DateTime!
  fraudScore: Float!
  decision: Decision!
  device: Device!
  ipAddress: String!
}

type User {
  id: ID!
  email: String
  createdAt: DateTime!
  transactionCount: Int!
  totalAmount: Float!
  fraudCases: [FraudCase!]!
  riskScore: Float!
  pagerank: Float!
  communityId: Int!
}

type TransactionGraph {
  nodes: [GraphNode!]!
  edges: [GraphEdge!]!
}

type GraphNode {
  id: ID!
  type: NodeType!
  label: String!
  properties: NodeProperties!
}

enum NodeType {
  USER
  MERCHANT
  DEVICE
  IP_ADDRESS
}

type GraphEdge {
  source: ID!
  target: ID!
  type: EdgeType!
  properties: EdgeProperties!
}

type ShapExplanation {
  transactionId: ID!
  baseValue: Float!
  features: [ShapFeature!]!
}

type ShapFeature {
  name: String!
  value: Float!
  shapValue: Float!  # Contribution to prediction
  importance: Float!
}

type Evidence {
  similarCases: [FraudCase!]!
  suspiciousPatterns: [Pattern!]!
  networkAnalysis: NetworkAnalysis!
}

type NetworkAnalysis {
  connectedFraudsters: [User!]!
  sharedDevices: [Device!]!
  communityRiskScore: Float!
}
```

**Task 4.2: GraphQL Resolvers**
```python
# File: backend/graphql/resolvers.py
import strawberry
from typing import List, Optional
from datetime import datetime

@strawberry.type
class User:
    id: strawberry.ID
    email: Optional[str]
    created_at: datetime
    risk_score: float
    pagerank: float
    community_id: int
    
    @strawberry.field
    async def transaction_count(self, info) -> int:
        # Efficient: Use dataloader to batch queries
        return await info.context["user_loader"].load(self.id)
    
    @strawberry.field
    async def fraud_cases(self, info) -> List["FraudCase"]:
        async with info.context["db_pool"].acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM fraud_cases WHERE user_id = $1",
                self.id
            )
            return [FraudCase.from_row(row) for row in rows]

@strawberry.type
class Query:
    @strawberry.field
    async def fraud_case(self, info, id: strawberry.ID) -> Optional["FraudCase"]:
        async with info.context["db_pool"].acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM fraud_cases WHERE id = $1",
                id
            )
            return FraudCase.from_row(row) if row else None
    
    @strawberry.field
    async def fraud_queue(
        self,
        info,
        status: Optional[FraudStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> "FraudQueueConnection":
        query = "SELECT * FROM fraud_cases WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = $1"
            params.append(status.value)
        
        query += f" ORDER BY created_at DESC LIMIT ${len(params)+1} OFFSET ${len(params)+2}"
        params.extend([limit, offset])
        
        async with info.context["db_pool"].acquire() as conn:
            rows = await conn.fetch(query, *params)
            cases = [FraudCase.from_row(row) for row in rows]
            total = await conn.fetchval("SELECT COUNT(*) FROM fraud_cases")
        
        return FraudQueueConnection(
            edges=[FraudCaseEdge(node=case) for case in cases],
            pageInfo=PageInfo(hasNextPage=(offset + limit) < total),
            totalCount=total
        )
    
    @strawberry.field
    async def suspicious_subgraph(
        self,
        info,
        user_id: strawberry.ID,
        hops: int = 2
    ) -> "TransactionGraph":
        # Query Neo4j for subgraph
        neo4j_driver = info.context["neo4j_driver"]
        
        with neo4j_driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})
                CALL apoc.path.subgraphAll(u, {
                    relationshipFilter: 'TRANSACTED_WITH>',
                    minLevel: 1,
                    maxLevel: $hops
                })
                YIELD nodes, relationships
                RETURN nodes, relationships
            """, user_id=user_id, hops=hops)
            
            record = result.single()
            nodes = [GraphNode.from_neo4j(n) for n in record['nodes']]
            edges = [GraphEdge.from_neo4j(r) for r in record['relationships']]
        
        return TransactionGraph(nodes=nodes, edges=edges)
    
    @strawberry.field
    async def shap_explanation(
        self,
        info,
        transaction_id: strawberry.ID
    ) -> "ShapExplanation":
        # Fetch from Redis cache or recompute
        redis_client = info.context["redis_client"]
        
        cached = redis_client.get(f"shap:{transaction_id}")
        if cached:
            return ShapExplanation.from_json(cached)
        
        # Recompute SHAP values
        import joblib
        shap_explainer = joblib.load('models/shap_explainer.pkl')
        
        # Fetch transaction features
        features = await fetch_transaction_features(transaction_id)
        shap_values = shap_explainer.shap_values(features)
        
        explanation = ShapExplanation(
            transaction_id=transaction_id,
            base_value=shap_explainer.expected_value,
            features=[
                ShapFeature(
                    name=feature_names[i],
                    value=features[i],
                    shap_value=shap_values[i],
                    importance=abs(shap_values[i])
                )
                for i in range(len(features))
            ]
        )
        
        # Cache for 15 minutes
        redis_client.setex(f"shap:{transaction_id}", 900, explanation.to_json())
        
        return explanation

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def label_case(
        self,
        info,
        id: strawberry.ID,
        label: FraudLabel,
        notes: Optional[str] = None
    ) -> "FraudCase":
        user_id = info.context["current_user"].id
        
        async with info.context["db_pool"].acquire() as conn:
            # Update case
            await conn.execute("""
                UPDATE fraud_cases
                SET status = $1, updated_at = NOW()
                WHERE id = $2
            """, label.value, id)
            
            # Add note
            if notes:
                await conn.execute("""
                    INSERT INTO case_notes (case_id, investigator_id, note, created_at)
                    VALUES ($1, $2, $3, NOW())
                """, id, user_id, notes)
            
            # Publish to Kafka for model retraining
            kafka_producer = info.context["kafka_producer"]
            kafka_producer.send('fraud.labels', {
                'transaction_id': id,
                'label': label.value,
                'investigator_id': user_id,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            # Fetch updated case
            row = await conn.fetchrow("SELECT * FROM fraud_cases WHERE id = $1", id)
            return FraudCase.from_row(row)

# FastAPI integration
from strawberry.fastapi import GraphQLRouter

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)

app.include_router(graphql_app, prefix="/graphql")

# Gotcha: Use DataLoader pattern to avoid N+1 query problem
# Gotcha: Implement query depth limiting to prevent abuse
```

**Task 4.3: DataLoader for Efficient Batching**
```python
# File: backend/graphql/dataloaders.py
from aiodataloader import DataLoader
from typing import List
import asyncpg

class UserLoader(DataLoader):
    def __init__(self, db_pool):
        super().__init__()
        self.db_pool = db_pool
    
    async def batch_load_fn(self, user_ids: List[str]) -> List[int]:
        """
        Batch load transaction counts for multiple users
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, COUNT(*) as txn_count
                FROM transactions
                WHERE user_id = ANY($1)
                GROUP BY user_id
            """, user_ids)
            
            # Create lookup dict
            counts = {row['user_id']: row['txn_count'] for row in rows}
            
            # Return in same order as input (important!)
            return [counts.get(user_id, 0) for user_id in user_ids]

class FeatureLoader(DataLoader):
    def __init__(self, feast_store):
        super().__init__()
        self.feast_store = feast_store
    
    async def batch_load_fn(self, user_ids: List[str]) -> List[dict]:
        """
        Batch load features from Feast
        """
        entity_rows = [{"user_id": uid} for uid in user_ids]
        features = self.feast_store.get_online_features(
            entity_rows=entity_rows,
            features=["transaction_features:txn_count_24h", "graph_features:pagerank"]
        ).to_dict()
        
        return [
            {
                'txn_count_24h': features['txn_count_24h'][i],
                'pagerank': features['pagerank'][i]
            }
            for i in range(len(user_ids))
        ]

# Usage in GraphQL context
async def get_context(request):
    return {
        "db_pool": request.app.state.db_pool,
        "neo4j_driver": request.app.state.neo4j_driver,
        "redis_client": request.app.state.redis_client,
        "kafka_producer": request.app.state.kafka_producer,
        "current_user": await get_current_user(request),
        "user_loader": UserLoader(request.app.state.db_pool),
        "feature_loader": FeatureLoader(request.app.state.feast_store)
    }

# Gotcha: DataLoader caches within a single request - don't reuse across requests
# Gotcha: batch_load_fn must return results in SAME ORDER as input keys
```

#### **Week 23-24: Frontend Development**

**Task 4.4: React Dashboard with Material-UI**
```typescript
// File: frontend/src/pages/FraudQueue.tsx
import React from 'react';
import { useQuery, gql } from '@apollo/client';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Button,
  CircularProgress
} from '@mui/material';
import { useNavigate } from 'react-router-dom';

const FRAUD_QUEUE_QUERY = gql`
  query FraudQueue($status: FraudStatus, $limit: Int, $offset: Int) {
    fraudQueue(status: $status, limit: $limit, offset: $offset) {
      edges {
        node {
          id
          transaction {
            id
            amount
            currency
            timestamp
            user {
              id
              email
            }
            merchant {
              id
              name
            }
          }
          fraudScore
          status
          createdAt
        }
      }
      pageInfo {
        hasNextPage
      }
      totalCount
    }
  }
`;

export const FraudQueue: React.FC = () => {
  const navigate = useNavigate();
  const [page, setPage] = React.useState(0);
  const limit = 50;
  
  const { data, loading, error } = useQuery(FRAUD_QUEUE_QUERY, {
    variables: {
      status: 'PENDING',
      limit,
      offset: page * limit
    },
    pollInterval: 5000  // Refresh every 5 seconds
  });
  
  if (loading) return <CircularProgress />;
  if (error) return <div>Error: {error.message}</div>;
  
  const cases = data.fraudQueue.edges.map(e => e.node);
  
  return (
    <div>
      <h1>Fraud Queue ({data.fraudQueue.totalCount} cases)</h1>
      
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Case ID</TableCell>
              <TableCell>User</TableCell>
              <TableCell>Merchant</TableCell>
              <TableCell>Amount</TableCell>
              <TableCell>Fraud Score</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Created</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {cases.map((fraudCase) => (
              <TableRow key={fraudCase.id}>
                <TableCell>{fraudCase.id.slice(0, 8)}</TableCell>
                <TableCell>{fraudCase.transaction.user.email}</TableCell>
                <TableCell>{fraudCase.transaction.merchant.name}</TableCell>
                <TableCell>
                  {fraudCase.transaction.amount.toFixed(2)} {fraudCase.transaction.currency}
                </TableCell>
                <TableCell>
                  <Chip
                    label={fraudCase.fraudScore.toFixed(2)}
                    color={
                      fraudCase.fraudScore > 0.7 ? 'error' :
                      fraudCase.fraudScore > 0.5 ? 'warning' : 'success'
                    }
                  />
                </TableCell>
                <TableCell>{fraudCase.status}</TableCell>
                <TableCell>{new Date(fraudCase.createdAt).toLocaleString()}</TableCell>
                <TableCell>
                  <Button
                    variant="contained"
                    size="small"
                    onClick={() => navigate(`/case/${fraudCase.id}`)}
                  >
                    Investigate
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      
      <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'space-between' }}>
        <Button disabled={page === 0} onClick={() => setPage(page - 1)}>
          Previous
        </Button>
        <span>Page {page + 1}</span>
        <Button
          disabled={!data.fraudQueue.pageInfo.hasNextPage}
          onClick={() => setPage(page + 1)}
        >
          Next
        </Button>
      </div>
    </div>
  );
};

// Gotcha: Use pollInterval for real-time updates (alternative to WebSocket subscriptions)
// Gotcha: Implement virtualized table (react-window) for >1000 rows
```

**Task 4.5: D3.js Network Visualization**
```typescript
// File: frontend/src/components/NetworkGraph.tsx
import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface Node {
  id: string;
  type: string;
  fraud: boolean;
  pagerank: number;
}

interface Link {
  source: string;
  target: string;
  amount: number;
}

interface NetworkGraphProps {
  nodes: Node[];
  links: Link[];
}

export const NetworkGraph: React.FC<NetworkGraphProps> = ({ nodes, links }) => {
  const svgRef = useRef<SVGSVGElement>(null);
  
  useEffect(() => {
    if (!svgRef.current) return;
    
    const width = 800;
    const height = 600;
    
    // Clear previous
    d3.select(svgRef.current).selectAll("*").remove();
    
    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height]);
    
    // Force simulation
    const simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id((d: any) => d.id).distance(100))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(30));
    
    // Links
    const link = svg.append("g")
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", (d: any) => Math.sqrt(d.amount / 100));
    
    // Nodes
    const node = svg.append("g")
      .selectAll("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d: any) => 5 + d.pagerank * 50)  // Size by PageRank
      .attr("fill", (d: any) => d.fraud ? "#f44336" : d.type === "USER" ? "#2196f3" : "#4caf50")
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .call(drag(simulation) as any);
    
    // Labels
    const label = svg.append("g")
      .selectAll("text")
      .data(nodes)
      .join("text")
      .text((d: any) => d.id.slice(0, 8))
      .attr("font-size", 10)
      .attr("dx", 12)
      .attr("dy", 4);
    
    // Tooltip
    node.append("title")
      .text((d: any) => `${d.id}\nType: ${d.type}\nPageRank: ${d.pagerank.toFixed(3)}\nFraud: ${d.fraud}`);
    
    // Update positions
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);
      
      node
        .attr("cx", (d: any) => d.x)
        .attr("cy", (d: any) => d.y);
      
      label
        .attr("x", (d: any) => d.x)
        .attr("y", (d: any) => d.y);
    });
    
    // Drag behavior
    function drag(simulation: any) {
      function dragstarted(event: any) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
      }
      
      function dragged(event: any) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
      }
      
      function dragended(event: any) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
      }
      
      return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
    }
  }, [nodes, links]);
  
  return (
    <div>
      <svg ref={svgRef}></svg>
      <div style={{ marginTop: '10px' }}>
        <span style={{ color: '#f44336' }}>● Fraudster</span>
        <span style={{ color: '#2196f3', marginLeft: '20px' }}>● User</span>
        <span style={{ color: '#4caf50', marginLeft: '20px' }}>● Merchant</span>
      </div>
    </div>
  );
};

// Gotcha: D3 force simulation is CPU-intensive - limit to <200 nodes
// Gotcha: Use React.memo() to prevent re-rendering on parent state changes
```

**Task 4.6: SHAP Visualization Component**
```typescript
// File: frontend/src/components/ShapChart.tsx
import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, Cell } from 'recharts';

interface ShapFeature {
  name: string;
  value: number;
  shapValue: number;
  importance: number;
}

interface ShapChartProps {
  features: ShapFeature[];
  baseValue: number;
}

export const ShapChart: React.FC<ShapChartProps> = ({ features, baseValue }) => {
  // Sort by absolute importance
  const sortedFeatures = [...features].sort((a, b) => b.importance - a.importance).slice(0, 10);
  
  // Prepare data for Recharts
  const data = sortedFeatures.map(f => ({
    name: f.name,
    shapValue: f.shapValue,
    value: f.value.toFixed(2)
  }));
  
  return (
    <div>
      <h3>SHAP Explanation (Top 10 Features)</h3>
      <p>Base Value (average prediction): {baseValue.toFixed(3)}</p>
      
      <BarChart width={600} height={400} data={data} layout="vertical">
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" />
        <YAxis dataKey="name" type="category" width={150} />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload || payload.length === 0) return null;
            const data = payload[0].payload;
            return (
              <div style={{ backgroundColor: 'white', padding: '10px', border: '1px solid #ccc' }}>
                <p><strong>{data.name}</strong></p>
                <p>Value: {data.value}</p>
                <p>SHAP: {data.shapValue.toFixed(4)}</p>
                <p>{data.shapValue > 0 ? 'Increases' : 'Decreases'} fraud probability</p>
              </div>
            );
          }}
        />
        <Bar dataKey="shapValue">
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.shapValue > 0 ? '#f44336' : '#4caf50'} />
          ))}
        </Bar>
      </BarChart>
      
      <div style={{ marginTop: '20px' }}>
        <p><strong>Interpretation:</strong></p>
        <ul>
          {sortedFeatures.slice(0, 3).map(f => (
            <li key={f.name}>
              <strong>{f.name}</strong> (value: {f.value.toFixed(2)}):{' '}
              {f.shapValue > 0 ? 'Increased' : 'Decreased'} fraud score by{' '}
              {Math.abs(f.shapValue).toFixed(3)}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

// Gotcha: SHAP values can be hard to interpret for non-technical users - add plain English explanations
// Gotcha: Use consistent color scheme (red = increases fraud, green = decreases fraud)
```

#### **Week 25-26: Case Management UI**

**Task 4.7: Case Detail Page**
```typescript
// File: frontend/src/pages/CaseDetail.tsx
import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, gql } from '@apollo/client';
import {
  Grid,
  Paper,
  Typography,
  Divider,
  Button,
  TextField,
  Select,
  MenuItem,
  Tabs,
  Tab
} from '@mui/material';
import { NetworkGraph } from '../components/NetworkGraph';
import { ShapChart } from '../components/ShapChart';

const CASE_DETAIL_QUERY = gql`
  query CaseDetail($id: ID!) {
    fraudCase(id: $id) {
      id
      transaction {
        id
        user {
          id
          email
          transactionCount
          riskScore
        }
        merchant {
          id
          name
        }
        amount
        currency
        timestamp
        device {
          id
          type
        }
      }
      fraudScore
      status
      notes {
        id
        investigator {
          name
        }
        note
        createdAt
      }
      evidence {
        similarCases {
          id
          fraudScore
        }
        networkAnalysis {
          connectedFraudsters {
            id
            email
          }
          communityRiskScore
        }
      }
    }
    
    suspiciousSubgraph(userId: $userId, hops: 2) {
      nodes {
        id
        type
        properties
      }
      edges {
        source
        target
        properties
      }
    }
    
    shapExplanation(transactionId: $transactionId) {
      baseValue
      features {
        name
        value
        shapValue
        importance
      }
    }
  }
`;

const LABEL_CASE_MUTATION = gql`
  mutation LabelCase($id: ID!, $label: FraudLabel!, $notes: String) {
    labelCase(id: $id, label: $label, notes: $notes) {
      id
      status
    }
  }
`;

export const CaseDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [tab, setTab] = useState(0);
  const [notes, setNotes] = useState('');
  
  const { data, loading, error } = useQuery(CASE_DETAIL_QUERY, {
    variables: {
      id,
      userId: data?.fraudCase?.transaction?.user?.id,
      transactionId: data?.fraudCase?.transaction?.id
    },
    skip: !id
  });
  
  const [labelCase] = useMutation(LABEL_CASE_MUTATION, {
    refetchQueries: ['FraudQueue']
  });
  
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  
  const fraudCase = data.fraudCase;
  const subgraph = data.suspiciousSubgraph;
  const shapExplanation = data.shapExplanation;
  
  const handleLabel = async (label: string) => {
    await labelCase({
      variables: { id, label, notes }
    });
    alert(`Case labeled as ${label}`);
  };
  
  return (
    <div style={{ padding: '20px' }}>
      <Typography variant="h4">Case #{id.slice(0, 8)}</Typography>
      
      <Grid container spacing={3} style={{ marginTop: '20px' }}>
        {/* Left column: Transaction details */}
        <Grid item xs={12} md={6}>
          <Paper style={{ padding: '20px' }}>
            <Typography variant="h6">Transaction Details</Typography>
            <Divider style={{ margin: '10px 0' }} />
            
            <p><strong>Transaction ID:</strong> {fraudCase.transaction.id}</p>
            <p><strong>User:</strong> {fraudCase.transaction.user.email}</p>
            <p><strong>Merchant:</strong> {fraudCase.transaction.merchant.name}</p>
            <p><strong>Amount:</strong> {fraudCase.transaction.amount} {fraudCase.transaction.currency}</p>
            <p><strong>Timestamp:</strong> {new Date(fraudCase.transaction.timestamp).toLocaleString()}</p>
            <p><strong>Device:</strong> {fraudCase.transaction.device.type}</p>
            
            <Divider style={{ margin: '20px 0' }} />
            
            <Typography variant="h6">Risk Assessment</Typography>
            <p><strong>Fraud Score:</strong> <span style={{ color: fraudCase.fraudScore > 0.7 ? 'red' : 'orange' }}>{fraudCase.fraudScore.toFixed(2)}</span></p>
            <p><strong>User Risk Score:</strong> {fraudCase.transaction.user.riskScore.toFixed(2)}</p>
            <p><strong>User Transaction Count:</strong> {fraudCase.transaction.user.transactionCount}</p>
          </Paper>
          
          {/* Evidence */}
          <Paper style={{ padding: '20px', marginTop: '20px' }}>
            <Typography variant="h6">Evidence</Typography>
            <Divider style={{ margin: '10px 0' }} />
            
            <p><strong>Similar Cases:</strong> {fraudCase.evidence.similarCases.length}</p>
            <p><strong>Connected Fraudsters:</strong> {fraudCase.evidence.networkAnalysis.connectedFraudsters.length}</p>
            <p><strong>Community Risk Score:</strong> {fraudCase.evidence.networkAnalysis.communityRiskScore.toFixed(2)}</p>
            
            {fraudCase.evidence.networkAnalysis.connectedFraudsters.length > 0 && (
              <div>
                <p><strong>Known fraudsters in network:</strong></p>
                <ul>
                  {fraudCase.evidence.networkAnalysis.connectedFraudsters.map(f => (
                    <li key={f.id}>{f.email}</li>
                  ))}
                </ul>
              </div>
            )}
          </Paper>
        </Grid>
        
        {/* Right column: Tabs */}
        <Grid item xs={12} md={6}>
          <Paper style={{ padding: '20px' }}>
            <Tabs value={tab} onChange={(e, v) => setTab(v)}>
              <Tab label="Network Graph" />
              <Tab label="SHAP Explanation" />
              <Tab label="Notes" />
            </Tabs>
            
            <div style={{ marginTop: '20px' }}>
              {tab === 0 && (
                <NetworkGraph
                  nodes={subgraph.nodes}
                  links={subgraph.edges}
                />
              )}
              
              {tab === 1 && (
                <ShapChart
                  features={shapExplanation.features}
                  baseValue={shapExplanation.baseValue}
                />
              )}
              
              {tab === 2 && (
                <div>
                  {fraudCase.notes.map(note => (
                    <div key={note.id} style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#f5f5f5' }}>
                      <p><strong>{note.investigator.name}</strong> - {new Date(note.createdAt).toLocaleString()}</p>
                      <p>{note.note}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Paper>
        </Grid>
      </Grid>
      
      {/* Action buttons */}
      <Paper style={{ padding: '20px', marginTop: '20px' }}>
        <Typography variant="h6">Decision</Typography>
        <Divider style={{ margin: '10px 0' }} />
        
        <TextField
          label="Notes"
          multiline
          rows={3}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          fullWidth
          style={{ marginBottom: '20px' }}
        />
        
        <div style={{ display: 'flex', gap: '10px' }}>
          <Button variant="contained" color="success" onClick={() => handleLabel('RESOLVED_LEGITIMATE')}>
            Mark Legitimate
          </Button>
          <Button variant="contained" color="error" onClick={() => handleLabel('RESOLVED_FRAUD')}>
            Confirm Fraud
          </Button>
          <Button variant="contained" color="warning" onClick={() => handleLabel('ESCALATED')}>
            Escalate
          </Button>
        </div>
      </Paper>
    </div>
  );
};

// Gotcha: Load subgraph and SHAP in parallel with Promise.all() to reduce latency
// Gotcha: Cache SHAP explanations aggressively (15min) - expensive to compute
```

---

## **V. Small Technical Details & "Gotchas"**

### **Data Engineering**

1. **Neo4j Index Performance**
   ```cypher
   CREATE INDEX user_id_index FOR (u:User) ON (u.id);
   CREATE INDEX timestamp_index FOR ()-[r:TRANSACTED_WITH]-() ON (r.timestamp);
   
   // Gotcha: Composite indexes for common queries
   CREATE INDEX user_merchant_index FOR ()-[r:TRANSACTED_WITH]-() ON (r.user_id, r.merchant_id);
   ```

2. **Kafka Consumer Group Rebalancing**
   ```python
   # Gotcha: Set session.timeout.ms higher to prevent rebalancing during slow processing
   consumer_config = {
       'session.timeout.ms': 60000,  # 60 seconds
       'heartbeat.interval.ms': 3000,  # Send heartbeat every 3s
       'max.poll.interval.ms': 300000  # 5 minutes
   }
   ```

3. **Feast Feature Consistency**
   ```python
   # Gotcha: Point-in-time joins prevent label leakage
   from feast import FeatureStore
   store = FeatureStore(repo_path=".")
   
   training_df = store.get_historical_features(
       entity_df=entity_df,  # Must include event_timestamp
       features=["transaction_features:txn_count_24h"],
       full_feature_names=True
   )
   
   # Gotcha: full_feature_names=True avoids column name conflicts
   ```

4. **Spark Memory Tuning**
   ```python
   # Gotcha: Default executor memory (1g) causes OOM
   spark_conf = SparkConf() \
       .set("spark.executor.memory", "8g") \
       .set("spark.executor.memoryOverhead", "2g") \
       .set("spark.driver.memory", "4g") \
       .set("spark.sql.shuffle.partitions", "20")
   ```

### **ML/Data Science**

5. **Graph Sampling for Large Graphs**
   ```python
   # Gotcha: Can't load 10M node graph into memory
   from torch_geometric.loader import NeighborLoader
   
   loader = NeighborLoader(
       data,
       num_neighbors=[15, 10],  # 2-hop sampling
       batch_size=32,
       input_nodes=train_mask
   )
   
   # Gotcha: Sampling introduces variance - use larger num_neighbors or mini-batch GNN
   ```

6. **SMOTE Pitfalls**
   ```python
   # WRONG: SMOTE on entire dataset (test set leakage)
   X_balanced, y_balanced = SMOTE().fit_resample(X, y)
   X_train, X_test, y_train, y_test = train_test_split(X_balanced, y_balanced)
   
   # RIGHT: SMOTE only on training set
   X_train, X_test, y_train, y_test = train_test_split(X, y)
   X_train_balanced, y_train_balanced = SMOTE().fit_resample(X_train, y_train)
   ```

7. **XGBoost Early Stopping**
   ```python
   # Gotcha: Without early stopping, model overfits
   model.fit(
       X_train, y_train,
       eval_set=[(X_val, y_val)],
       early_stopping_rounds=20,
       verbose=False
   )
   
   # Use best iteration, not final iteration
   best_iteration = model.best_iteration
   ```

8. **SHAP TreeExplainer Speed**
   ```python
   # Slow: KernelExplainer (model-agnostic)
   explainer = shap.KernelExplainer(model.predict, X_train[:100])
   
   # Fast: TreeExplainer (tree models only)
   explainer = shap.TreeExplainer(model)
   
   # Gotcha: TreeExplainer only works for tree-based models (XGBoost, RandomForest)
   ```

### **Backend/MLOps**

9. **FastAPI Async Database**
   ```python
   # WRONG: Blocking call in async function
   @app.get("/user/{id}")
   async def get_user(id: str):
       user = db.query(User).filter_by(id=id).first()  # Blocks event loop!
       return user
   
   # RIGHT: Use async database driver
   @app.get("/user/{id}")
   async def get_user(id: str):
       async with db_pool.acquire() as conn:
           user = await conn.fetchrow("SELECT * FROM users WHERE id=$1", id)
           return user
   ```

10. **Redis Pipeline for Batch Operations**
    ```python
    # Slow: 100 round trips
    for user_id in user_ids:
        redis.get(f"features:{user_id}")
    
    # Fast: 1 round trip
    pipe = redis.pipeline()
    for user_id in user_ids:
        pipe.get(f"features:{user_id}")
    results = pipe.execute()
    ```

11. **MLflow Model Registry Stage Transitions**
    ```python
    # Gotcha: archive_existing_versions=True moves old Production to Archived
    client.transition_model_version_stage(
        name="fraud_ensemble",
        version=3,
        stage="Production",
        archive_existing_versions=True  # Important!
    )
    ```

12. **Evidently HTML Report Size**
    ```python
    # Gotcha: HTML reports are 50MB+ for large datasets
    report.run(
        reference_data=reference_data.sample(1000),  # Sample!
        current_data=current_data.sample(1000)
    )
    
    # Or save as JSON instead of HTML
    report.save_json('drift_report.json')
    ```

### **Frontend**

13. **GraphQL Query Depth Limiting**
    ```typescript
    // Prevent malicious deep queries
    import depthLimit from 'graphql-depth-limit';
    
    const schema = makeExecutableSchema({
      typeDefs,
      resolvers,
      validationRules: [depthLimit(5)]  // Max 5 levels deep
    });
    ```

14. **Apollo Client Cache Normalization**
    ```typescript
    const cache = new InMemoryCache({
      typePolicies: {
        FraudCase: {
          keyFields: ["id"],  // Use id as cache key
        },
        User: {
          keyFields: ["id"],
        }
      }
    });
    
    // Gotcha: Without keyFields, cache can't deduplicate entities
    ```

15. **D3.js Memory Leaks**
    ```typescript
    useEffect(() => {
      const svg = d3.select(svgRef.current);
      // ... visualization code ...
      
      return () => {
        svg.selectAll("*").remove();  // Cleanup!
        simulation.stop();
      };
    }, [data]);
    
    // Gotcha: Force simulations keep running if not stopped
    ```

16. **Material-UI Table Virtualization**
    ```typescript
    // Gotcha: Rendering 10K rows causes lag
    import { FixedSizeList } from 'react-window';
    
    <FixedSizeList
      height={600}
      itemCount={cases.length}
      itemSize={50}
      width="100%"
    >
      {({ index, style }) => (
        <div style={style}>
          <CaseRow case={cases[index]} />
        </div>
      )}
    </FixedSizeList>
    ```

### **DevOps**

17. **Kubernetes Resource Requests vs Limits**
    ```yaml
    resources:
      requests:
        cpu: "1000m"
        memory: "2Gi"
      limits:
        cpu: "2000m"  # 2x request
        memory: "4Gi"  # 2x request
    
    # Gotcha: CPU is throttled at limit, memory triggers OOM kill
    # Gotcha: requests determine scheduling, limits prevent noisy neighbors
    ```

18. **Horizontal Pod Autoscaler**
    ```yaml
    apiVersion: autoscaling/v2
    kind: HorizontalPodAutoscaler
    metadata:
      name: fraud-api-hpa
    spec:
      scaleTargetRef:
        apiVersion: apps/v1
        kind: Deployment
        name: fraud-api
      minReplicas: 3
      maxReplicas: 20
      metrics:
      - type: Resource
        resource:
          name: cpu
          target:
            type: Utilization
            averageUtilization: 70
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300  # Wait 5min before scaling down
    
    # Gotcha: Without stabilizationWindow, HPA thrashes (scale up/down rapidly)
    ```

19. **PostgreSQL Connection Pooling**
    ```python
    # Gotcha: asyncpg connection pool size should match max workers
    db_pool = await asyncpg.create_pool(
        dsn="postgresql://...",
        min_size=10,
        max_size=20,
        max_queries=50000,  # Close connection after 50K queries (prevent leaks)
        max_inactive_connection_lifetime=300  # Close idle connections after 5min
    )
    ```

20. **Prometheus Metric Cardinality**
    ```python
    # BAD: High cardinality (1M unique user_ids)
    prediction_counter = Counter('predictions', 'Predictions', ['user_id', 'model'])
    
    # GOOD: Low cardinality
    prediction_counter = Counter('predictions', 'Predictions', ['model', 'decision'])
    
    # Gotcha: High cardinality metrics cause Prometheus to OOM
    ```

---

## **Summary**

**Project 2: GraphGuard** is a complete, production-grade fraud detection system that demonstrates mastery across all four disciplines:

1. **Data Engineering**: Kafka streaming, Neo4j graph construction, Spark feature engineering, Feast feature store, Airflow orchestration
2. **Data Science**: EDA, XGBoost baseline, Graph Neural Networks (GAT), SHAP explainability, statistical A/B testing
3. **ML Engineering**: Model serving with FastAPI, semantic caching, drift detection with Evidently AI, automated retraining with Ray, MLflow model registry
4. **Software Engineering**: GraphQL API with DataLoader optimization, React dashboard with Material-UI, D3.js network visualization, case management workflow

**All integrated into ONE cohesive system** where:
- Transactions flow from Kafka → Neo4j → Feature Store → ML Models → Investigators
- Every component is observable, scalable, and production-ready
- Full audit trail for regulatory compliance (SOC2, PCI-DSS, GDPR)

