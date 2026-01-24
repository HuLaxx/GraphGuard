# GraphGuard - Infrastructure

Infrastructure as Code and local observability configs.

## Structure

```
infrastructure/
├── terraform/        # AWS resources (template)
│   └── main.tf
├── prometheus/       # Prometheus config
│   └── prometheus.yml
├── neo4j/            # Index scripts
│   └── indexes.cypher
└── backup/           # Backup scripts
    └── backup_strategy.py
```

## Cloud Resources (Template)
- VPC + Subnets
- EKS Kubernetes Cluster
- RDS Aurora PostgreSQL
- MSK (Managed Kafka)
- ElastiCache Redis
- S3 Buckets (data lake, models, logs)

## Reference
See `terraform/main.tf` for the current template.
