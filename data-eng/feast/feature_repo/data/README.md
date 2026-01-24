# Feast Data Directory

This directory contains local Parquet files for Feast offline store (development mode).

In production, these would be stored in S3:
- s3://graphguard/features/transaction_features.parquet
- s3://graphguard/features/graph_features.parquet
- s3://graphguard/features/merchant_features.parquet

## Commands

```bash
# Apply feature definitions
feast apply

# Materialize features to online store (Redis)
feast materialize-incremental $(date -u +"%Y-%m-%dT%H:%M:%S")

# Get features for inference
feast get-online-features \
  --features transaction_features:txn_count_1h \
  --features graph_features:pagerank \
  --entity user_id=user_123
```
