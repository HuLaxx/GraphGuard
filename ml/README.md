# GraphGuard - Machine Learning

This directory contains all ML training, serving, and monitoring components.

## Structure

```
ml/
├── training/         # Model training scripts
├── serving/          # FastAPI inference API
├── monitoring/       # Drift detection, performance monitoring
└── experimentation/  # A/B test analysis
```

## Models
- **XGBoost**: Baseline gradient boosting on tabular features
- **GAT (Graph Attention Network)**: GNN on transaction graph
- **Ensemble**: Weighted combination (0.6*XGB + 0.4*GAT)

## Reference
See [Specification.md Lines 1883-2727](../Specification.md) for detailed implementation.
