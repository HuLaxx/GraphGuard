# FleetFlow — Reproducible Telemetry Lake Replay

**Status:** Local batch replay implementation. Not connected to live Kafka, AWS, a production fleet, or a completed dispatch workflow.

This slice demonstrates an actual **raw → validated → curated** data journey for historical vehicle telemetry. It uses intentionally synthetic Glasgow-area coordinates with made-up IDs; no customer or driver records are represented as genuine.

## Reproduce locally

Requires Python 3.11+ and network access to install dependencies:

~~~bash
cd backend
python -m pip install -e ".[dev,lake]"
python -m src.lakehouse.replay \
  --input tests/fixtures/demo_gps_events.jsonl \
  --output /tmp/fleetflow-lake \
  --lateness-minutes 15
python -m pytest tests/test_lakehouse/test_replay.py -v
~~~

All replay runs are immutable and addressed by a digest of the input bytes **and the lateness configuration**. Re-running the same fixture should return the existing snapshot, rather than overwrite history.

The CLI prints the exact output directory, source SHA-256 and reconciliation counts. It also records SHA-256 checksums for each artifact, and refuses to reuse a snapshot if any artifact changes.

## Data contract and provenance

Input is newline-delimited JSON containing the existing FleetFlow GPSLocationEvent v1 contract (event_id, schema_version=1, timestamp with timezone, driver/vehicle UUIDs, coordinates, optional speed). Input event_id, timestamp, schema_version and event_type are required explicitly at the replay boundary (even though producers can generate defaults). Event timestamps are normalised to UTC; schema version, event type, coordinates and timestamps are validated.

### Actual output layout

~~~text
/tmp/fleetflow-lake/runs/<run-key>/
├── manifest.json
├── raw/
│   └── events.jsonl                       # exact input bytes
├── clean/
│   └── event_date=YYYY-MM-DD/
│       └── telemetry.parquet              # validated, deduplicated events
├── curated/
│   └── hourly_vehicle_telemetry.parquet   # event counts and speed summaries
└── quarantine/
    └── rejected.jsonl                     # line and diagnostic, not copied payload
~~~

**Clean layer:** Parquet stores UUIDs, UTC timestamps, version, geolocation, speed, a late-event flag and the original input line for traceability. Each event ID appears at most once within a snapshot.

**Curated layer:** One row per vehicle per UTC hour with event count, late count, average reported speed and most recent event position. The most recent event is selected by *event time*, not arrival order.

**Quarantine:** Invalid JSON, wrong event type/version, missing or naive timestamps and bad coordinates are rejected with limited diagnostic information. Repeated identical event IDs count as duplicates; the same event ID with a conflicting payload goes to quarantine instead of quietly overriding earlier state.

**Late events:** Arrival-order watermark is tracked per vehicle. Events older than the highest previously observed event-time by more than the configured lateness threshold are flagged, but retained in historical analytics. This demonstrates replay/backfill semantics, not a complete streaming watermark implementation.

**Manifest:** Source digest, run key, contract identifier, lateness threshold, artifact paths and reconciliation totals are generated without invented performance claims or wall-clock-dependent metadata.

## Acceptance tests

The automated tests check:
1. A known event produces raw bytes, date-partitioned clean Parquet and a real curated Parquet table.
2. Two dates produce separate partitions; duplicates do not inflate KPI counts.
3. One deliberately late event is flagged and retained.
4. Conflicting IDs, invalid geolocation, unsupported schema versions and missing timezone information are rejected.
5. A repeated replay is immutable; changed input or lateness configuration produces a new run.
6. A fully invalid source still produces typed empty Parquet tables plus an inspectable quarantine.
7. Missing identity/time metadata is rejected, and tampered persisted files fail replay integrity checks.

### Verified PR evidence — 12 November 2026

- [GitHub Actions run 43289821451](https://github.com/HuLaxx/FleetFlow/actions/runs/43289821451) completed successfully on code commit 4f0507d31fece4f9df5554c78f8309a337d6f15b.
- Backend test job: **49 passed, 3 warnings**; **six lakehouse replay tests passed**, verifying actual PyArrow/Parquet output, deduplication, late detection, quarantine, identity/time contract, immutable replay and checksum tampering detection.
- Backend coverage reported **60% overall**; this is not comprehensive integration coverage.
- Backend Ruff/Black, frontend lint/types/build, ML CPU smoke and high/critical dependency security scan all passed in that run.

A passing replay suite does **not** verify a live Kafka producer, Postgres/TimescaleDB integration, dbt marts, Airflow DAGs, WebSocket telemetry or AWS hosting.

## Known limitations and next engineering gate

- **Batch-only:** This script reads a local JSONL snapshot; no live Kafka subscription, incremental Kafka checkpoint or DLQ integration has been claimed.
- **No relational sink:** It produces Parquet, not production PostgreSQL updates.
- **No object-storage deployment:** The directory layout can be mapped to S3 later, but no AWS resources have been provisioned.
- **Single writer:** Simultaneous writes to the same run key are not coordinated across processes.
- **Memory use:** Accepted rows are currently held in memory. For very large datasets, stream to bounded Parquet row groups and use external-state deduplication.
- **PII:** Store only permitted, non-sensitive and appropriately anonymised telemetry outside demo fixtures.
- **Data quality:** Expand to contract registry, alertable quality metrics, reconciliation across live consumers and backfill policy.
- **Next golden path:** Seed orders → ingest and validate events → persist route candidate → explicitly approve route → track GPS event → reconcile a curated dispatch-performance mart.

## Career relevance

This demonstrates event-time correctness, schema validation, event identity and duplicates, partitioned Parquet, quarantine, replay and deterministic analytical calculations. It is evidence of a **local data engineering prototype**, not evidence of a professionally operated cloud production system.
