# FleetFlow lakehouse pipeline

A batch data platform for FleetFlow's delivery data: **bronze → quality gate → silver (PySpark) → gold (dbt star schema)**, orchestrated by Airflow, deployable to Databricks on Azure with Terraform, and verified end to end in CI.

```
 bronze/                quality.py                  spark_job.py                    dbt_warehouse/
 raw CSV per table ──▶  contracts, quarantine ──▶  conformed Parquet,        ──▶  star schema (DuckDB or
 (generate.py,          and a pass-rate gate        dedupe, derived metrics,       Snowflake): 5 dims,
  seeded + defects)     (fails the run)             partitioned by date            incremental fact, KPIs
                                                    (idempotent overwrite)         + 30-odd dbt tests
          └───────────── Airflow DAG: lakehouse_daily.py (one logical date per run, backfill-safe) ─────────────┘
```

## What each part does

| Layer | Code | What it proves |
| --- | --- | --- |
| Synthetic source data | `generate.py` | Seeded, byte-for-byte reproducible data for 6 tables, with known injected defects (nulls, out-of-range values, unknown keys, invalid statuses, late duplicates). |
| Data contracts + quality gate | `quality.py` | Schema, type, not-null, accepted-value, range and foreign-key checks; bad rows go to `quarantine/` with reasons; late duplicates keep the newest version; the run fails if a table's pass rate drops below the threshold. |
| Silver (PySpark) | `spark_job.py` | Explicit schemas with `FAILFAST`, window-based dedupe, derived on-time / lateness / ingest-latency columns, partitioned Parquet with dynamic partition overwrite, so re-runs and backfills never duplicate rows. Runs locally, on Databricks or any Spark 3.5 cluster. |
| Gold (dbt) | `../dbt_warehouse/` | Star schema: `dim_date`, `dim_depot`, `dim_vehicle`, `dim_driver`, `dim_customer`, incremental `fct_deliveries` (unique key + lookback window for late data) and `fct_daily_depot_kpis`. Same SQL runs on DuckDB (CI) and Snowflake. Tested with unique, not-null, relationship, accepted-value and custom tests. |
| Orchestration | `../airflow/dags/lakehouse_daily.py` | Daily DAG, one logical date per run, retries with backoff, ordered backfills. |
| Databricks | `../databricks/databricks.yml` | Asset bundle that runs the Spark job as a serverless job (Free Edition compatible). |
| Infrastructure | `../../infra/azure-lakehouse/` | Terraform: ADLS Gen2 lake with bronze/silver/gold/quarantine containers, lifecycle policy, Databricks workspace + access connector (managed identity, no storage keys), Key Vault, Log Analytics. |
| CI | `../../.github/workflows/lakehouse.yml` | Runs every test (including Spark), the full pipeline, an incremental dbt re-run, a silver-vs-gold reconciliation, `terraform validate`, and posts the measured results on the PR. |

## Run it locally

```bash
pip install "pyspark==3.5.3" "pandas==2.2.3" "numpy<2" pytest dbt-duckdb duckdb   # Java 17 required for Spark
export PYTHONPATH=data-engineering

python -m lakehouse.generate --out data/lakehouse --days 30 --orders-per-day 2000
python -m lakehouse.quality  --root data/lakehouse --min-pass-rate 0.95
python -m lakehouse.spark_job --root data/lakehouse --start-date 2026-01-01 --end-date 2026-01-30
(cd data-engineering/dbt_warehouse && dbt build --profiles-dir .)

python -m pytest data-engineering/lakehouse/tests -v          # Spark tests skip if PySpark is missing
python -m lakehouse.benchmark --root data/lakehouse --days 30 --orders-per-day 5000
```

To run the gold layer on Snowflake instead, set `DBT_TARGET=snowflake` and the `SNOWFLAKE_*` variables listed in `dbt_warehouse/profiles.yml`, and load the silver Parquet into a `SILVER` schema (for example through an external stage on the ADLS `silver` container).

## Evidence

All numbers come from synthetic data and are for comparing changes, not production performance.

**Measured locally** (sandbox, Python 3.x, pandas; 30 days × 5,000 orders, seed 42, 1% injected defects):

| Stage | Rows | Time | Throughput |
| --- | ---: | ---: | ---: |
| Generate (bronze CSV) | 305,435 | 1.5 s | ~202,000 rows/s |
| Quality gate | 305,435 | 2.1 s | ~148,000 rows/s |

Quality gate on that run: orders pass rate 99.2%, deliveries 99.0%; every injected defect class is quarantined (checked by the tests).

**Measured in CI** ([PR #25](https://github.com/HuLaxx/FleetFlow/pull/25), GitHub-hosted runner, same dataset, Spark 3.5.3, dbt-duckdb 1.9):

| Stage | Rows | Time | Throughput |
| --- | ---: | ---: | ---: |
| Generate (bronze CSV) | 305,435 | 1.7 s | ~176,000 rows/s |
| Quality gate | 305,435 | 2.1 s | ~143,000 rows/s |
| Spark silver, cold run | 148,506 fact rows | 10.6 s | ~14,000 rows/s |
| Spark silver, idempotent re-run | 148,506 (no duplicates) | 2.5 s | |
| dbt build, full / incremental re-run | 38 models + tests | 4.3 s / 2.8 s | |

- Tests: 15 passed (including 4 Spark integration tests); 83% line coverage of the lakehouse package.
- dbt: 38 of 38 nodes passed on both the full build and the incremental re-run.
- Reconciliation: 148,506 silver rows = 148,506 gold rows; overall on-time rate 76.9%, success rate 94.0% (synthetic).
- Terraform: `fmt` clean and `validate` passed (azurerm 3.117).

Every pull request re-runs this and posts the results as a comment, plus a `lakehouse-evidence` artifact (logs, coverage, benchmark JSON, quarantine files).

## Known limits

- The Airflow DAG compiles but is not executed in CI (Airflow isn't installed there).
- The repo's older `Backend Tests` workflow was already failing on `main` before this pipeline was added; it is unrelated to the lakehouse code.
- `databricks.yml` and the Terraform are validated syntactically only; nothing is deployed, so no cloud costs are incurred.
- The Snowflake target uses the same SQL as DuckDB but hasn't been run against a live Snowflake account.
