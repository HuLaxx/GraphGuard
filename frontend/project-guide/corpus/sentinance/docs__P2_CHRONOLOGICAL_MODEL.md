# P2 chronological ridge AR(1) evaluation

The baseline evaluator and trainable ridge AR(1) use the same verified local curated Parquet snapshot and same held-out timestamps. A model observes the past log return and predicts the next log return. Hyperparameters are fixed candidates; select by validation MAE, ties prefer larger regularization. Refit once on all pre-test targets. Test uses rolling observed history, fixed coefficients; no test fitting or selection. Compare last-close, five-bar mean and ridge using MAE/RMSE/mean error. No resampling gaps, future target features, or implied trade profitability. JSON is deterministic within an identical runtime and exclusive output creation prevents accidental overwrite. The printed SHA-256 identifies the report. Model version, coefficients, split timestamps, source, snapshot ID, manifest hash and predictions are in the report.

Example from apps/api (operator supplies independent manifest hash and explicit boundaries):
`python forecast_model.py /path/to/snapshot --manifest-sha256 HASH --source fixture_exchange --symbol BTCUSDT --train-end 12 --validation-end 18 --output report.json`

CI synthetic cases check known trends and constant prices, invalid splits, leakage by mutating test values, and pinned Parquet provenance. Not evidence of real-market predictive performance, live arrival-time availability, LSTM superiority, or fully secured ML registry. A historical market dataset with verified rights, arrival timestamps, out-of-sample comparison and deployment review remain necessary.

Prior P1 receipt and repair test [44726728919](https://github.com/HuLaxx/Sentinance/actions/runs/44726728919) passed 26 tests. [Quality run](https://github.com/HuLaxx/Sentinance/actions/runs/44726728846) reported two formatting differences, fixed in this batch. Exact head CI must report success before release.

The dedicated acceptance workflow uploads the synthetic pinned-Parquet forecast JSON and SHA-256 digest as `synthetic-pinned-parquet-forecast-report` (14-day retention). These contain fixture data only, not live market performance. The older Ruff 0.1.8 gate also found five E721 type-comparison violations despite modern lint passing; use explicit bool rejection with isinstance, preserving strict integer validation rather than suppressing the checks.
