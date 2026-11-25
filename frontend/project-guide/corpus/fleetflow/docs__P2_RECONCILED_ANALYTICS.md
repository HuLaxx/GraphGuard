# FleetFlow P2 — reconciled analytics on two explicitly separate source paths

**Review:** [draft PR #10](https://github.com/HuLaxx/FleetFlow/pull/10), stacked on [draft PR #9](https://github.com/HuLaxx/FleetFlow/pull/9). No main merge, AWS resources, public historical GPS feed or paid service.

## Actual lineage

```text
Synthetic or exported GPS JSONL (bounded, offline)
  -> immutable raw/events.jsonl and source SHA-256
  -> Pydantic GPS v1 validation, source-order watermark, dedupe/quarantine
  -> clean/event_date=YYYY-MM-DD/*.parquet (UTC event time + late flag)
  -> curated/hourly_vehicle_telemetry.parquet
  -> independent quality.py reconciliation and artifact audit
```

This is **not** a live Kafka-to-S3 pipeline: live Kafka-to-PostGIS-to-WebSocket
was independently established in [P1 GPS acceptance](P1_AUTHENTICATED_GPS_END_TO_END.md).
The Parquet replay currently reads an explicitly supplied JSONL file.

```text
PostGIS transactional orders, drivers, routes (current state)
  -> dbt PostgreSQL staging views (privacy-reduced driver rows)
  -> dbt Postgres daily KPI fact + driver-performance dimension
  -> 26 dbt schema/relationship-style/singular SQL quality checks
  -> deterministic synthetic fixture assertions
```

The dbt models are **not** derived from the Parquet telemetry, and should not
be described as such. Current-state order and route tables are not a
historical event log; rebuilding the dbt marts makes snapshot aggregates, not
immutable as-of-date history.

## Semantics and privacy

- Route statuses include `planned` (not approved), `approved`,
  `in_progress`, `completed`, `cancelled`.
- Actual distance/duration and observed-vs-planned comparisons stay **NULL**
  when absent. A zero completed count is a legitimate zero; unobserved
  performance is **not** a legitimate 0% or 100% score.
- Only completed routes with **both** an actual and a positive planned
  distance are compared for distance ratio. Do not mix all planned routes
  into this denominator.
- dbt driver staging/marts intentionally omit name, email, phone and address.
  The raw transactional database still contains sensitive fields and must be
  access-controlled independently. Do not publish exported GPS files.
- Late GPS events within the immutable replay are retained and marked; they
  are not silently discarded. Duplicate event IDs with conflicting payloads
  are quarantined. Cross-layer validation independently checks hourly
  counts, last coordinates, average speed, late counts, partition dates,
  source-row arithmetic, content hashes and missing/extra rows.
- The fixture data in `data-engineering/dbt/ci/seed_postgis.sql` and
  `backend/tests/fixtures/demo_gps_events.jsonl` is deterministic,
  **synthetic**, and not actual fleet/customer performance.

## Reproduce locally (only a disposable test database)

Prerequisites: Python 3.11, a local disposable PostgreSQL 15 + PostGIS
database **named `fleetflow_test`** with user `fleetflow`, and the
dependencies below. Never run the CI fixture SQL against operational data.

```bash
python -m pip install -e './backend[dev,lake]'
python -m pip install 'dbt-postgres>=1.9,<2'

export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=fleetflow
export POSTGRES_PASSWORD='<your local test password>'
export POSTGRES_DB=fleetflow_test
export JWT_SECRET_KEY='<locally generated 32+ character test key>'
export DBT_HOST=localhost
export DBT_PORT=5432
export DBT_USER=fleetflow
export DBT_PASSWORD="$POSTGRES_PASSWORD"
export DBT_DATABASE=fleetflow_test
export DBT_SCHEMA=public

python data-engineering/dbt/ci/bootstrap_test_db.py
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U fleetflow -d fleetflow_test \
  -v ON_ERROR_STOP=1 -1 -f data-engineering/dbt/ci/seed_postgis.sql

dbt build --profiles-dir data-engineering/dbt --project-dir data-engineering/dbt --full-refresh
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U fleetflow -d fleetflow_test \
  -v ON_ERROR_STOP=1 -1 -f data-engineering/dbt/ci/assert_fixture_outcomes.sql

python -m pytest backend/tests/test_lakehouse/test_replay.py -q
python -m pytest backend/tests/test_lakehouse/test_quality.py -q
python -m src.lakehouse.replay \
  --input backend/tests/fixtures/demo_gps_events.jsonl --output /tmp/fleetflow-gps-replay
# Inspect /tmp/fleetflow-gps-replay/runs/<run-key>/manifest.json.
python -m src.lakehouse.quality --run /tmp/fleetflow-gps-replay/runs/<run-key>
```

The last two commands are separate: `replay` prints the content-addressed
run directory, then `quality` audits that exact directory. Do **not**
literally enter `<run-key>`; substitute the printed value.

## Verified inspectable CI

**Code SHA `7d00451821f42cd198e16d5d87ae7ccb6f5a374e`**:
[Analytics run 44105602510](https://github.com/HuLaxx/FleetFlow/actions/runs/44105602510)
passed both jobs:
- Real PostGIS + dbt **5 models, 26 data tests, 31 successful tasks**
  (`PASS=31 WARN=0 ERROR=0`) and exact synthetic KPI SQL assertion.
- Real PyArrow **12 replay tests + 6 quality tests passed**.
- CI preserves `manifest.json` and `run_results.json` as workflow artifacts.
Earlier fixture-setup failures revealed required driver hours and order source
fields; both are now explicitly seeded. The dbt run demonstrates model
execution, not S3/Athena or a production dashboard.

## Still missing (do not score as complete)

- Continuously replicated source to raw lake (currently manual batch replay).
- Incremental tracked ingestion and point-in-time historical snapshots;
  no CDC/incremental dbt model is yet verified.
- An actually executed Airflow scheduling run, retries/backfill operations,
  warehouse freshness alerting, data lineage artifacts for the full real
  dispatch event chain, provider outage tests.
- Held-out routing and demand/ETA baseline evaluation with measured, timestamped
  costs and accuracy, p95 latency and cloud cost analysis.
- Terraform plan/validate, human-approved optional AWS deployment/teardown,
  production privacy/retention and authenticated multi-worker socket fanout.
