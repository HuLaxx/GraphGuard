# GraphGuard - Data Engineering

This directory contains all data engineering components for the GraphGuard fraud detection platform.

## Structure

```
data-eng/
├── producers/        # Kafka producers (transaction ingestion)
├── consumers/        # Kafka consumers (graph builder, etc.)
├── flink/            # Apache Flink CEP jobs
├── spark/            # Spark feature engineering
├── feast/            # Feature store configuration
├── airflow/          # Orchestration DAGs
├── neo4j/            # Graph algorithms & queries
└── great_expectations/  # Data quality
```

## Reference
See [Specification.md Lines 716-1315](../Specification.md) for detailed implementation.
