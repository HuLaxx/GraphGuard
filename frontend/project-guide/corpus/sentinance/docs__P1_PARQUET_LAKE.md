# P1 local Parquet evidence snapshots

**Status:** review-only [PR #35](https://github.com/HuLaxx/Sentinance/pull/35). This is an **offline, local data-lake slice**, not an S3/AWS deployment or proof of exchange licensing. The user-facing site, model and agent are not connected.

## Reproducible path

The focused integration workflow uses a **synthetic aggregate-trade HTTP fixture**, a **real disposable Kafka broker**, and **real disposable PostgreSQL**. It publishes source-owned versioned events, persists them with consumer-position/source-ID uniqueness, then exports the PostgreSQL raw-event ledger into three local Parquet files:

```
synthetic HTTP aggregate trade with stable upstream ID
     ↓ validate source fields (ID, price, quantity, observed UTC time)
Kafka sentinance.prices.v1 → broker ack
     ↓
PostgreSQL raw_kafka_price_events → unique source/symbol/event ID
     ↓
local immutable snapshot directory (SHA-256 content address)
     ├── raw/raw.parquet             Kafka position + upstream raw JSON
     ├── validated/validated.parquet typed source/time/price/quantity
     ├── curated/minute_bars.parquet UTC-minute OHLCV and trade-qty VWAP
     └── manifest.json              row counts, time range, file checksums
```

A 1-minute bar groups aggregate trades by **source, instrument and observed UTC minute**. Price columns use PostgreSQL/Arrow-compatible decimal precision rather than early floating-point coercion. The `base_volume` is aggregate trade base quantity, **not** dollar volume. VWAP is weighted by this source quantity, **not** a future-looking forecast. Missing or zero volume gives null VWAP.

The exporter revalidates stored source JSON against the materialized PostgreSQL columns. A mismatched, nonfinite or malformed source record blocks export. Files are written to a staging directory then the completed snapshot directory is renamed into place. Data snapshots are content-addressed and immutable: a late event generates a *different* snapshot, retaining earlier versions for comparison. Each manifest includes SHA-256 file hashes, and `verify_snapshot` checks all three expected layers before accepting a snapshot.

## Manual isolated replay

1. Use a local isolated PostgreSQL and Kafka service with an explicitly reviewed connection string. Run the additive migration `alembic upgrade head` on **this isolated environment only**.
2. Populate the v1 raw ledger using the opt-in source fixture/test workflow, or a provider after an actual data-rights check. Don't fabricate exchange IDs.
3. Install the optional PyArrow dependency from the tested focused CI environment (`pyarrow==21.0.0`), and run `P1_LOCAL_LAKE_EXPORT_ENABLED=1 python price_lake_worker.py --output-dir ./local-price-lake` from `apps/api`.
4. Run the three-layer snapshot tests via `pytest -q -o addopts="" tests/unit/test_price_lake_parquet.py`; the dedicated GitHub Actions workflow installs PyArrow so they **must pass**, not silently skip.
5. Inspect `manifest.json`, compare its file SHA-256 values, open `raw`, `validated` and `curated` files, and read the source IDs/timestamps before using any derived metrics.

Do **not** run a live exchange HTTP request merely to populate a demo. No paid infrastructure is needed for this fixture-based test.

## Evidence and limitations

- [ ] Record exact final-head passing GitHub Actions integration/quality run IDs; test code is not evidence until run.
- [ ] Verify real source authorization, upstream rate limits and a recoverable durable source cursor; the current source runner still uses an **operator-supplied cursor** and a bounded batch.
- [ ] Upgrade snapshots to measured incremental partitioned raw→validated→curated S3-compatible storage, query reconciliation and schema evolution tests before claiming a production lake.
- [ ] Handle multiple concurrent exporter writers with a lock/compare-and-swap strategy, late-data correction audit and object storage retention policy.
- [ ] Connect curated bars to a versioned model/indicator baseline, agent trace and live/mock-labeled API/frontend.
- [ ] Run load/latency benchmarks; do not claim performance, prediction returns, AWS deployment or exactly-once end-to-end guarantees from this local smoke path.

All PRs remain drafts; no main merge, production DB migration, network deployment or paid cloud resources are authorized.
