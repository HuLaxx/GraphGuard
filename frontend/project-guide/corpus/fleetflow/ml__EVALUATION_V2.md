# FleetFlow ML evaluation — redesign branch

This work upgrades the **evaluation and packaging pipeline**, not the trained
model's measured predictive accuracy. Do not advertise an accuracy uplift
until real order data, reproducible backtests, and an external holdout support it.

## What changed

- The forecasting module/package naming collision is fixed.
- ML package exports load lazily, avoiding unrelated optional dependency imports.
- Rolling features use past observations only.
- Train/validation splits are chronological.
- Feature and target scalers are fitted **only on training samples per fold**.
- The LSTM restores the best validation epoch instead of the last epoch.
- Model MAE is compared to a last-observation naive baseline in **order counts**.
- Model weights have matching preprocessing metadata saved for inference.

## Run

Install the ML package's required Python dependencies in an isolated environment.

```bash
python -m pytest ml/tests/test_forecasting_validation.py -q
python -m ml.training.train_forecaster --epochs 10 --seed 42
```

Training defaults to generated **synthetic** hourly demand data. That is
appropriate for software testing, not claims of real-world forecast accuracy.
The training script writes fold reports under `ml/training/metrics/` (or
`ML_METRICS_DIR`) and model/preprocessing artifacts under
`ml/training/artifacts/`.

## Model acceptance gates

1. Backtest on a versioned, timezone-normalized real demand dataset.
2. Report per-zone and per-hour MAE against seasonal naive baselines.
3. Use a final untouched time holdout after model selection.
4. Reject models that do not beat the baseline; never silently substitute
   synthetic predictions or invented confidence scores.
5. Deploy the approved model with version, training-data timestamp, inference
   latency, uncertainty interval and monitoring metadata.
6. Track model drift and data freshness before enabling dispatch recommendations.

## Next product integrations

Demand heatmaps from approved forecasts, operational ETA risk, traffic-aware
rerouting through a road network service, capacity and driver-duty constraints,
human approval of optimized plans, and transparent explanation of why a
proposed dispatch differs from the current manifest.

The browser-only Dispatch Lab remains a **simulation**. It is not served by
the PyTorch or OR-Tools backend and should never be labeled as model inference.
