# Pipeline observability

Answers three operational questions about FleetFlow's batch pipelines:

1. **Did the pipeline run, and did it work?** Every task run is recorded (start,
   finish, duration, rows, error) and exported as Prometheus metrics.
2. **Is the source data fresh?** dbt source freshness SLAs on the raw tables,
   with each dbt verdict re-derived independently from the timestamps.
3. **Will someone be told?** Failed runs and stale sources produce alerts
   (webhook with retries and de-duplication, or logs), and Prometheus alert
   rules cover the same conditions plus "the freshness check stopped running".

Standard library only (Python 3.10+), so it runs inside Airflow workers, CI
steps and cron jobs without adding dependencies.

## Status

| Part | Status |
| --- | --- |
| Run store (JSONL, SQL via DB-API), `track_run`, `track` CLI | Implemented, unit-tested; SQL store tested on SQLite and PostgreSQL 16 in CI |
| dbt source freshness SLAs (`data-engineering/dbt/models/schema.yml`) | Implemented; CI runs real `dbt source freshness` against PostGIS with a **synthetic** stale -> recovered scenario |
| Prometheus metrics (textfile collector) + alert rules | Implemented; `promtool check`/`test rules` and a live node_exporter + Prometheus run in CI |
| Webhook alerts | Implemented; delivered to a local receiver in CI. No real Slack/Teams/PagerDuty endpoint is configured |
| Airflow callbacks | Wired into `daily_optimization` and `hourly_forecast` via an optional import; callbacks are unit-tested with Airflow-shaped contexts, **not** in a running Airflow |

## How it fits together

```
Airflow task / CI step / cron
  |  on_failure_callback / on_success_callback / `track -- <cmd>`
  v
run store (runs.jsonl or ops_pipeline_runs) --run-metrics--> runs.prom ----.
                                                                            |
dbt source freshness -> target/sources.json --freshness--> freshness.prom --+--> node_exporter (textfile)
                                     |                                            -> Prometheus rules
                                     '--> alerts (webhook or log)                    (monitoring/alerts)
```

## Freshness SLAs

| Source table | `loaded_at_field` | warn after | error after |
| --- | --- | --- | --- |
| `raw.orders` | `created_at` | 6 h | 24 h |
| `raw.drivers` | `updated_at` | 24 h | 72 h |
| `raw.routes` | `updated_at` | 24 h | 48 h |
| `raw.route_stops` | `updated_at` | 24 h | 48 h |
| depots, vehicles, customers | - | no SLA (reference data) | |

These are starting values for a daily dispatch cycle, not numbers agreed
with a real operations team.

## Usage

```bash
pip install -e data-engineering/observability

# Wrap any step: records the run, writes metrics, alerts if it fails.
python -m fleetflow_observability track --store out/runs.jsonl --alert \
  --pipeline dbt --task source_freshness --expected-interval-seconds 3600 \
  --metrics-out monitoring/textfile/runs.prom -- \
  dbt source freshness --project-dir data-engineering/dbt --output "$PWD/out/sources.json"

# Turn dbt's artifact into metrics, a Markdown summary and alerts; gate on errors.
python -m fleetflow_observability freshness --sources-json out/sources.json \
  --metrics-out monitoring/textfile/freshness.prom --summary-md out/freshness.md \
  --alert --fail-on error
```

In Python:

```python
from fleetflow_observability import JsonlRunStore, track_run
from fleetflow_observability.alerts import dispatcher_from_env

with track_run("daily_optimization", "solve", JsonlRunStore("out/runs.jsonl"),
               dispatcher_from_env(), expected_interval_seconds=86400) as run:
    run.rows_out = solve_and_count()
```

Environment variables (nothing secret lives in the repository):

| Variable | Effect |
| --- | --- |
| `FLEETFLOW_ALERT_WEBHOOK_URL` | Post alerts here (http/https only); otherwise they are logged |
| `FLEETFLOW_ALERT_DEDUP_STATE` / `FLEETFLOW_ALERT_DEDUP_MINUTES` | Suppress repeats of the same alert within the window (default 60 min) |
| `FLEETFLOW_RUN_STORE_PATH` | JSONL run store used by the Airflow callbacks |

Exit codes for `freshness`: `0` ok, `1` a source is at or above `--fail-on`,
`2` unreadable artifact or a verdict that disagrees with `--expect` or with the
independent recomputation. `track` returns the wrapped command's exit code.

## Metrics and alerts

| Metric | Meaning |
| --- | --- |
| `fleetflow_pipeline_last_run_success` | 1/0 for the latest finished run per `pipeline`,`task` |
| `fleetflow_pipeline_last_run_duration_seconds`, `..._last_run_rows_out` | Latest run size and duration |
| `fleetflow_pipeline_last_success_timestamp_seconds`, `..._expected_interval_seconds` | Drives the missed-schedule alert |
| `fleetflow_pipeline_runs_total{status}` | Runs in the store |
| `fleetflow_source_freshness_status_code` | 0 pass, 1 warn, 2 error, 3 runtime error |
| `fleetflow_source_freshness_age_seconds`, `..._warn_after_seconds`, `..._error_after_seconds` | Age and thresholds |
| `fleetflow_source_freshness_check_timestamp_seconds` | When the check last ran |

Alert rules in [`monitoring/alerts/pipeline_alerts.yml`](../../monitoring/alerts/pipeline_alerts.yml):
`FleetflowPipelineRunFailed`, `FleetflowPipelineMissedSchedule`,
`FleetflowSourceFreshnessWarn` (15 min), `FleetflowSourceFreshnessError`,
`FleetflowFreshnessCheckNotRunning` (3 h). Their unit tests are in
`monitoring/alerts/tests/`.

## Tests

```bash
cd data-engineering/observability
python -m pytest            # PostgreSQL store test runs when FLEETFLOW_TEST_POSTGRES_DSN is set
```

CI: [`.github/workflows/observability.yml`](../../.github/workflows/observability.yml)
posts its results, including log tails for failed jobs, as a PR comment.
