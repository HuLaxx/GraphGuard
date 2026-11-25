# FleetFlow P2 — chronological demand baselines and manual-only Airflow

[Draft PR #12](https://github.com/HuLaxx/FleetFlow/pull/12),
stacked on [draft PR #11](https://github.com/HuLaxx/FleetFlow/pull/11).

## What changed, and why

Before this review, the old `daily_route_optimization` Airflow DAG contained a
hard-coded NYC depot, called an obsolete optimization API path, and wrote
route/stop rows directly without a dispatcher approval. The old
`hourly_demand_forecast` DAG synthesized demand **5** when missing and
advertised an uncalibrated **0.8 confidence**, with invented driver-positioning
guidance. Both were enabled on fixed automatic schedules.

Both are now **`schedule_interval=None` (manual-only)**, `catchup=False`,
and `max_active_runs=1`. The dispatch DAG runs only read-only, aggregate SQL
after receiving an explicit date and a configured synchronous PostgreSQL
connection. The forecasting DAG requires an operator-provided, validated
hourly CSV; it does not insert routes, send driver instructions, or serve
guessed confidence. Every actual route plan remains in the authenticated
FastAPI plan/approve workflow.

The optional Airflow 2.8.2 Docker dev profile now uses
`SequentialExecutor`, compatible with its local SQLite metadata database.
It mounts `backend` and `dags` read-only, binds the UI to localhost and
uses an ignored local input directory. This profile remains **development
only**, not a production HA scheduler.

## Baseline contract

`backend/src/analytics/forecast_baselines.py` validates a strict UTC
hourly sequence with zero missing/duplicate/unordered hours and nonnegative
integer counts. It accepts a CSV with exactly `timestamp_utc,count`, or
creates a deterministic synthetic 12-week fixture with seed 42. Input rows
never contain customer, vehicle or employee identities.

The evaluation uses the last **168 hours** as a chronological holdout and
an expanding one-hour-ahead walk-forward protocol: each prediction uses
actual observations strictly **before** its target time. Four naive baselines
(last-hour, same hour yesterday, same hour last week, trailing 24-hour mean)
are compared using **MAE, RMSE and WAPE**. WAPE is `null` when the entire
test period has zero demand (rather than inventing 100% accuracy).
There is no random-split leakage or "ML superiority" claim.

This is not Prophet/XGBoost/LSTM training, future 24-hour multi-step model
validation or evidence of accuracy on real orders. It is the **minimum
reproducible control benchmark** those models must beat on a future
real-life, privacy-reviewed chronological dataset.

## Reproduce the synthetic baseline

```bash
python -m pip install -e './backend[dev]'
python -m pytest backend/tests/test_analytics/test_forecast_baselines.py -v
python -m src.analytics.forecast_baselines \
  --weeks 12 --seed 42 --holdout-hours 168 \
  --output /tmp/fleetflow-synthetic-forecast-results.json
python -m json.tool /tmp/fleetflow-synthetic-forecast-results.json
```

For an explicitly supplied **hourly anonymous count CSV**:
```bash
python -m src.analytics.forecast_baselines \
  --input /path/to/hourly_counts.csv --holdout-hours 168 \
  --output /tmp/fleetflow-validated-baselines.json
```
Any missing hour, duplicate, naive timezone or additional PII column makes
the input validation fail rather than silently filling it.

## Local manual Airflow usage

The `data` Compose profile is optional. After manually reviewing
`.env` and Docker credentials, put a **non-sensitive** hourly CSV in
`data-engineering/airflow/input/` (this folder is gitignored).
Configure `FLEETFLOW_HOURLY_COUNTS_CSV` to the **container path**
`/opt/fleetflow/input/YOUR_FILE.csv`.
For dispatch readiness, set `FLEETFLOW_ANALYTICS_DATABASE_URL` to a
**synchronous** PostgreSQL URL with SELECT-only permissions; the task also
uses `SET TRANSACTION READ ONLY`. No file or SQL result should contain
a driver's GPS coordinates or customer address.

Run the Airflow profile manually, open the loopback-only UI, and trigger
`daily_route_optimization` with `{"route_date":"2030-01-15"}`, or
`hourly_demand_forecast` with an explicitly supplied source path. This is
a **manual evaluation**. There is no ongoing daily dispatch, actual
automatic ETA pipeline, or production cron in this PR.

## CI and evidence

- [Forecast/Airflow CI 44110285107](https://github.com/HuLaxx/FleetFlow/actions/runs/44110285107) at code SHA
  `c037568a99d916f1eb3c8490a80e23a69caea49a`:
  **6 chronological/negative tests passed**; four synthetic baseline
  predictions were evaluated; official **Airflow 2.8.2 DAGBag import passed**
  with both manual-only DAGs and zero import errors. Earlier Airflow parsing
  correctly caught `datetime.UTC` unavailable on its Python 3.8 image,
  repaired to `timezone.utc`.
- Synthetic fixed-seed, one-step 168h holdout:
  `last_hour` MAE 3.7857, `last_day` 2.5774,
  `last_week` 2.1250, `trailing_day_mean` 5.1863
  (units: synthetic orders/hour, **not production accuracy**).
- Python 3.11 Ruff requires a documented exception for the
  Python 3.8-compatible `timezone.utc` spelling. Later code/Compose/docs
  commits require **matching exact-head CI** before calling PR #12 green.

## Outstanding P2/P3/P4

No production Airflow scheduling or event-time warehouse backfill, automatic
Kafka → Parquet capture, performance SLA or data retention policy. Routes
still use approximate fixed-speed Haversine. Real holdout datasets,
multi-step forecasting, actual route impacts, Terraform plan/validate, AWS
budget and IAM sign-off, cloud teardown, full system cost and public portfolio
case study are separate gates. Neither the optional Airflow profile nor
the synthetic baselines has been deployed to real operations.
