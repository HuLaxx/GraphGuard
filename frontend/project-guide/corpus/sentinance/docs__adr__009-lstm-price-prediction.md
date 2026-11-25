# ADR 009: LSTM for Price Prediction

**Status:** Accepted  
**Date:** 2026-01-22

## Context

Sentinance needs price prediction for:
- 1-hour, 24-hour, 7-day horizons
- Multiple assets (crypto + indices)
- Confidence scores for user guidance

## Decision

Use **LSTM (Long Short-Term Memory)** neural networks trained on historical price data.

## Model Architecture

```
Input (60 timesteps, 1 feature)
    ↓
LSTM (128 units, return_sequences=True)
    ↓
Dropout (0.2)
    ↓
LSTM (64 units)
    ↓
Dropout (0.2)
    ↓
Dense (64, ReLU)
    ↓
Dense (1, Linear)
    ↓
Output (predicted price)
```

## Training Pipeline

```python
# 1. Download 5 years of hourly data
df = yf.Ticker("BTC-USD").history(period="5y", interval="1h")

# 2. Normalize with Min-Max scaling
prices_normalized = (prices - min) / (max - min)

# 3. Create sequences (60 timesteps lookback)
X, y = create_sequences(prices_normalized, lookback=60)

# 4. Train with 70/15/15 split
model.fit(X_train, y_train, epochs=50, validation_data=(X_val, y_val))

# 5. Log to MLflow
mlflow.pytorch.log_model(model, "model")
```

## Consequences

### Positive
- Captures temporal patterns
- Proven for time-series
- PyTorch integration with MLflow

### Negative
- Training time (30-60 min per model)
- Requires retraining for market regime changes
- GPU beneficial but not required

## Fallback

When trained model unavailable, use ensemble of:
- Momentum prediction
- Mean reversion

```python
if not model_available:
    return ensemble_prediction(momentum, mean_reversion)
```
