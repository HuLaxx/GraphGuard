# Sentinance ML Models

## Overview

This directory contains machine learning models for price prediction and market analysis.

## Models

### LSTM Price Prediction (`lstm_model.py`)

A PyTorch LSTM (Long Short-Term Memory) model for time-series price prediction.

**Architecture:**
- Input: 60 time steps of OHLCV data (5 features)
- Hidden: 2 LSTM layers with 64 units each
- Output: Next price prediction

**Usage:**
```python
from lstm_model import LSTMModel, ModelConfig, Trainer

# Create model
config = ModelConfig(
    input_size=5,
    hidden_size=64,
    num_layers=2,
    sequence_length=60
)
model = LSTMModel(config)

# Train
trainer = Trainer(model, config)
trainer.train(train_loader, val_loader)

# Predict
from lstm_model import predict
prediction = predict(model, data, device)
```

### GNN Market Analysis (`gnn_model.py`)

Graph Neural Network for analyzing relationships between assets.

---

## Training

### Prerequisites
```bash
pip install torch scikit-learn yfinance
```

### Train LSTM Model
```bash
cd apps/api
python train_model.py --symbol BTCUSDT --epochs 100
```

### Train on All Symbols
```bash
python train_universal_model.py
```

---

## Model Files

| File | Description |
|------|-------------|
| `models/lstm_v1.pt` | Pre-trained LSTM checkpoint |
| `models/scaler.pkl` | Feature scaler |

> **Note**: Model files (`.pt`, `.pkl`) are gitignored. The system runs in mock mode if no model is found.

---

## MLflow Integration

Track experiments with MLflow:

```bash
# Start MLflow server (via Docker)
docker compose -f docker-compose.dev.yml up -d mlflow

# Access UI
open http://localhost:5000
```

---

## Performance

| Symbol | MAE | RMSE | Training Time |
|--------|-----|------|---------------|
| BTCUSDT | ~2.1% | ~2.8% | ~5 min |
| ETHUSDT | ~2.3% | ~3.1% | ~5 min |

*Results may vary based on market conditions and training data.*
