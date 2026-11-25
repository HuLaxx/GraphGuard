# P1 — Source-identifiable aggregate trades (fixture and opt-in provider)

**Draft milestone:** a bounded **Binance spot aggregate-trade** source adapter,
connected through the existing versioned Kafka producer to the PostgreSQL
durable consumer. It is **not** on by default and is not wired into the
current live WebSocket UI, ML predictor or agent.

## Why the original 24-hour ticker is not sufficient

The pre-existing ticker/price-stream code takes local fetch timestamps and
does not carry a stable upstream event identity. It would be misleading to
invent a unique trade ID from those snapshots and claim to support exact
source replay. This adapter uses the provider's `a` (aggregate trade ID) and
`T` (provider trade timestamp, **milliseconds**); it preserves the provider
price `p` and quantity `q` as **decimal strings** and notes the provider
`f`, `l`, and `m` metadata in `provenance`.

- Topic: `sentinance.prices.v1` (same opt-in durable topic as PR #31)
- Sources: `binance_aggtrade` for opt-in real provider requests and
  `binance_aggtrade_fixture` for synthetic HTTP fixtures; these identities
  intentionally cannot collide in the durable ledger
- Identity: `(source, symbol, aggregate trade ID)` in PostgreSQL
- Timestamp: `T` from provider, normalized to UTC
- Provenance: explicit `mode=fixture` in offline CI and seeded demos,
  `mode=provider` only in the opt-in live CLI. All new fixture records use
  a **different source namespace** from real provider records
- Fetch: one bounded REST page using a known `fromId`, up to 1000 records;
  validates every record and strict aggregate-trade ID continuity *before*
  sending any Kafka records
- Failure: missing/duplicated/out-of-order IDs fail closed; transport and
  HTTP 5xx errors use at most three bounded jittered attempts. HTTP 418/429
  and other 4xx fail immediately. An interrupted Kafka publish can leave an
  acknowledged prefix: rerun using the same upstream IDs and rely on the
  transactional source/symbol/event ID key rather than a made-up exactly-once
  claim.

## Manual provider mode (requires conscious opt-in)

From `apps/api`, with approved local Kafka/Postgres resources and
`alembic upgrade head` already applied, separately start the durable
consumer:

```bash
P1_DURABLE_PRICE_SINK_ENABLED=1 python durable_price_worker.py
```

Only after reviewing the **actual** Binance Spot REST API terms, regional
availability, request weights and data-license restrictions, run an explicit
bounded one-page request in a second terminal:

```bash
SENTINANCE_BINANCE_LIVE_ENABLED=1 python binance_ingest_once.py \
  --symbol BTCUSDT --from-id <verified_upstream_aggregate_id> --limit 100
```

**Do not use a made-up `from-id`:** obtain a real aggregate-trade ID from
the source. Do not begin automated backfills or polling without a reviewed
checkpoint, rate-limit and license policy. No real provider access was used
to establish the code's CI pass.

The source documentation for `a`, `p`, `q`, `T` and inclusive `fromId`
is the official Binance Spot REST market-data endpoint:
https://developers.binance.com/en/docs/binance-spot-api-docs/rest-api/market-data-endpoints
The separate Binance historical **dataset** may be covered by
non-commercial/share-alike terms:
https://github.com/binance/binance-public-data/blob/master/TERMS_AND_CONDITIONS.md
Do not assume REST access and dataset redistribution have identical licenses.

## Verification and remaining gaps

- Unit tests use only `httpx.MockTransport` and label all source records
  `mode=fixture`. They check provider IDs/times, rate limits, HTTP failures,
  malformed numbers and strict gap behavior.
- The dedicated `P1 Durable Kafka PostgreSQL` CI job additionally uses a
  **fixture HTTP response**, a real disposable Kafka broker, a real
  PostgreSQL instance migrated through Alembic, and an independent
  consumer. It verifies persisted price precision, `fixture` provenance,
  source identity and broker retry deduplication after two records actually
  reach the sink.
- The live exchange API and its regional availability have **not** been
  confirmed by a real request. Data rates, licensing and provider
  operational health remain pending.
- Still missing: durable source cursor, source-ID gap backfill, late-event
  watermarks, raw/validated/curated Parquet layers, provider-quality
  marts and end-to-end UI/agent trace with staleness and live/mock labels.
- No automatic PR merge, production deployment, paid AWS services, financial
  trading execution or claim of profitability.
