# GraphGuard - Infrastructure

Infrastructure as Code and Kubernetes manifests.

## Structure

```
infrastructure/
├── terraform/        # AWS/GCP resources
│   ├── main.tf
│   ├── variables.tf
│   └── outputs.tf
├── k8s/              # Kubernetes manifests
│   ├── base/
│   └── monitoring/
└── helm/             # Helm value overrides
    ├── kafka-values.yaml
    ├── neo4j-values.yaml
    └── redis-values.yaml
```

## Cloud Resources (from Specification.md Lines 95-118)
- VPC + Subnets
- EKS Kubernetes Cluster
- RDS Aurora PostgreSQL
- MSK (Managed Kafka)
- ElastiCache Redis
- S3 Buckets (data lake, models, logs)

## Reference
See [Specification.md Lines 83-118](../Specification.md) for cloud services details.
