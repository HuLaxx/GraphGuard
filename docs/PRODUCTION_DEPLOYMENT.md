# GraphGuard Production Deployment Guide

## Prerequisites

- **Docker & Docker Compose** (v2.0+)
- **Kubernetes** (v1.25+) with `kubectl` configured
- **Helm** (v3.10+)
- **AWS CLI** configured with appropriate permissions
- **Terraform** (v1.5+) for infrastructure provisioning

---

## 1. Infrastructure Setup

### 1.1. AWS Infrastructure (Terraform)

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan -var-file="prod.tfvars"

# Apply infrastructure
terraform apply -var-file="prod.tfvars"
```

This provisions:
- **RDS Aurora PostgreSQL** (db.r6g.large)
- **ElastiCache Redis** (cache.r6g.large)
- **MSK Kafka** (3-broker cluster)
- **EKS Kubernetes** (managed node group)
- **S3 Buckets** (models, backups, data lake)
- **VPC** with private subnets

### 1.2. Neo4j Deployment

```bash
# Option A: Neo4j Aura (Managed)
# Create cluster at https://console.neo4j.io

# Option B: Self-hosted on K8s
helm repo add neo4j https://helm.neo4j.com/neo4j
helm install neo4j neo4j/neo4j \
  --set neo4j.password=$NEO4J_PASSWORD \
  --set volumes.data.mode=dynamic \
  --set volumes.data.dynamic.storageClassName=gp3
```

### 1.3. Apply Neo4j Indexes

```bash
# Connect to Neo4j
cypher-shell -u neo4j -p $NEO4J_PASSWORD

# Run indexes
:source infrastructure/neo4j/indexes.cypher
```

---

## 2. Secrets Management

### 2.1. AWS Secrets Manager

```bash
# Create secrets
aws secretsmanager create-secret \
  --name graphguard/production \
  --secret-string file://.env.production

# Reference in Kubernetes
kubectl create secret generic graphguard-secrets \
  --from-literal=POSTGRES_PASSWORD=$(aws secretsmanager get-secret-value \
    --secret-id graphguard/production --query SecretString --output text | jq -r '.POSTGRES_PASSWORD')
```

### 2.2. Environment Variables

```bash
# Copy template
cp .env.production.template .env.production

# Edit with secure values
vim .env.production

# Validate
python -c "from dotenv import dotenv_values; print(dotenv_values('.env.production'))"
```

---

## 3. Database Setup

### 3.1. PostgreSQL Migrations

```bash
# Set database URL
export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:5432/${POSTGRES_DB}"

# Run migrations
cd backend
alembic upgrade head

# Verify
alembic current
```

### 3.2. Kafka Topics

```bash
# Create topics
kafka-topics.sh --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS \
  --create --topic transactions.raw \
  --partitions 12 --replication-factor 3

kafka-topics.sh --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS \
  --create --topic fraud.patterns \
  --partitions 6 --replication-factor 3

kafka-topics.sh --bootstrap-server $KAFKA_BOOTSTRAP_SERVERS \
  --create --topic fraud.scores \
  --partitions 6 --replication-factor 3
```

---

## 4. Build & Push Images

### 4.1. Build Docker Images

```bash
# Set registry
export REGISTRY=123456789.dkr.ecr.us-east-1.amazonaws.com

# Build images
docker build -t $REGISTRY/graphguard-api:$(git rev-parse --short HEAD) -f docker/Dockerfile.api .
docker build -t $REGISTRY/graphguard-frontend:$(git rev-parse --short HEAD) -f docker/Dockerfile.frontend .
docker build -t $REGISTRY/graphguard-flink:$(git rev-parse --short HEAD) -f docker/Dockerfile.flink .

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $REGISTRY
docker push $REGISTRY/graphguard-api:$(git rev-parse --short HEAD)
docker push $REGISTRY/graphguard-frontend:$(git rev-parse --short HEAD)
docker push $REGISTRY/graphguard-flink:$(git rev-parse --short HEAD)
```

### 4.2. Upload ML Models

```bash
# Upload models to S3
aws s3 cp models/xgboost_rigorous/xgboost_fraud.json \
  s3://graphguard-models/production/xgboost_fraud_v2.json

aws s3 cp models/gat/gat_fraud.pth \
  s3://graphguard-models/production/gat_fraud_v2.pth
```

---

## 5. Kubernetes Deployment

### 5.1. Deploy with Helm

```bash
# Add Helm repo
helm repo add graphguard https://charts.graphguard.io

# Install/Upgrade
helm upgrade --install graphguard ./infrastructure/helm/graphguard \
  --namespace graphguard --create-namespace \
  --values infrastructure/helm/graphguard/values-prod.yaml \
  --set image.tag=$(git rev-parse --short HEAD)
```

### 5.2. Verify Deployment

```bash
# Check pods
kubectl get pods -n graphguard

# Check services
kubectl get svc -n graphguard

# Check ingress
kubectl get ingress -n graphguard

# View logs
kubectl logs -f deployment/graphguard-api -n graphguard
```

---

## 6. Load Testing

### 6.1. Run Load Tests

```bash
# Install k6
brew install k6  # or download from https://k6.io

# Run smoke test
k6 run --env BASE_URL=https://api.graphguard.yourdomain.com \
       --env API_KEY=$API_KEY \
       --env SCENARIO=smoke \
       tests/load/k6_load_test.js

# Run full load test
k6 run --env SCENARIO=load tests/load/k6_load_test.js
```

### 6.2. Expected Results

| Metric | Target | Acceptable |
|--------|--------|------------|
| Fraud Score p95 | <100ms | <150ms |
| Error Rate | <0.1% | <1% |
| Request Rate | >1000 req/s | >500 req/s |

---

## 7. Monitoring Setup

### 7.1. Prometheus & Grafana

```bash
# Install kube-prometheus-stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --set grafana.adminPassword=$GRAFANA_PASSWORD
```

### 7.2. Import Dashboards

```bash
# Import GraphGuard dashboards
kubectl apply -f infrastructure/monitoring/grafana-dashboards.yaml
```

### 7.3. Alerting

Configure alerts in Grafana:
- **API Latency > 200ms** (p95)
- **Error Rate > 1%**
- **Redis/Neo4j Down**
- **Kafka Consumer Lag > 10000**

---

## 8. Backup & Recovery

### 8.1. Automated Backups

```bash
# Schedule daily backups (run via CronJob)
kubectl apply -f infrastructure/k8s/backup-cronjob.yaml
```

### 8.2. Manual Backup

```bash
# PostgreSQL
pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER $POSTGRES_DB | gzip > backup_$(date +%Y%m%d).sql.gz
aws s3 cp backup_$(date +%Y%m%d).sql.gz s3://graphguard-backups/postgres/

# Neo4j
neo4j-admin database dump --database=neo4j --to-path=/backups/neo4j
aws s3 sync /backups/neo4j s3://graphguard-backups/neo4j/
```

### 8.3. Restore

```bash
# PostgreSQL
aws s3 cp s3://graphguard-backups/postgres/backup_YYYYMMDD.sql.gz .
gunzip -c backup_YYYYMMDD.sql.gz | psql -h $POSTGRES_HOST -U $POSTGRES_USER $POSTGRES_DB

# Neo4j
neo4j-admin database load --database=neo4j --from-path=/backups/neo4j
```

---

## 9. Rollback Procedures

### 9.1. Application Rollback

```bash
# Helm rollback
helm rollback graphguard <revision> -n graphguard

# Or kubectl
kubectl rollout undo deployment/graphguard-api -n graphguard
```

### 9.2. Database Rollback

```bash
# Alembic downgrade
alembic downgrade -1  # One revision back
alembic downgrade <revision_id>  # Specific revision
```

---

## 10. Health Checks

### Production Endpoints

| Endpoint | Expected |
|----------|----------|
| `GET /health` | `{"status": "healthy"}` |
| `GET /metrics` | Prometheus metrics |
| `GET /docs` | OpenAPI documentation |

### Verification Script

```bash
#!/bin/bash
API_URL="https://api.graphguard.yourdomain.com"

# Health check
curl -s $API_URL/health | jq .

# Authenticated request
curl -s -H "X-API-Key: $API_KEY" \
  -X POST $API_URL/score \
  -H "Content-Type: application/json" \
  -d '{"transaction_id":"test_001","user_id":"u1","merchant_id":"m1","amount":100,"device_id":"d1","ip_address":"1.1.1.1"}' | jq .
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `Connection refused to Redis` | Check ElastiCache security groups |
| `Neo4j auth failed` | Verify NEO4J_PASSWORD in secrets |
| `Kafka consumer lag high` | Scale Flink task managers |
| `Model not found` | Verify S3 model path and IAM permissions |

### Support

- **Logs**: `kubectl logs -f deployment/graphguard-api`
- **Metrics**: Grafana dashboard at `/monitoring`
- **Alerts**: PagerDuty integration configured
