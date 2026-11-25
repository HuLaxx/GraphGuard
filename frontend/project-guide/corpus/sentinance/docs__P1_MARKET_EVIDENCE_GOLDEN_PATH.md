# P1 — Reproduce source → Kafka → PostgreSQL → API → browser

**Status:** First deterministic fixture-data journey on draft
[PR #33](https://github.com/HuLaxx/Sentinance/pull/33), stacked on review
PRs #31 and #32. It does **not** prove real Binance API access,
live production deployment, rate-limit compliance or an ML prediction.

## Proven and inspectable boundaries

```
Synthetic aggregate-trade fixture (clearly mode=fixture)
  -> httpx.MockTransport (no provider network call)
  -> strict Binance aggregate-trade adapter (source ID and UTC time)
  -> Kafka sentinance.prices.v1 (broker acknowledged)
  -> durable PostgreSQL transaction (source+symbol+ID unique)
  -> FastAPI GET /api/v1/market-events
  -> Next.js /data/evidence (Zod parsed, never fakes a missing API)
```

The source field for fixture events is
`binance_aggtrade_fixture`, while explicitly enabled real requests use
`binance_aggtrade`. This prevents fixture IDs from colliding with real
provider IDs in the same database. The provider timestamp is sourced from
the trade response; only the database `received_at` clock is local.

The API returns only a bounded read-only slice (up to 50 events), including
raw decimal strings, `observed_at`, `received_at`, source event identity,
`fixture/provider/unverified` origin and `recent/stale/future_timestamp`
freshness. It *always* returns `live_feed_verified=false`: a source field
or recent timestamp does not confirm an actively connected exchange.

For a missing Postgres schema/database the API fails with HTTP 503, not a
successful empty response. For an empty ledger it returns
`status=no_data` and no manufactured prices. A missing frontend backend
setting produces a visible unavailable message.

## Reproduce locally with *development-only* resources

The existing `infra/docker-compose.yml` defines local PostgreSQL and
Kafka-compatible Redpanda containers. It uses development credentials and
has not been promoted to a production installation. Before running, review
ports, resource requirements and local dependencies.

1. In the repository root start only the two local dependencies:

   ```bash
   docker compose -f infra/docker-compose.yml up -d postgres redpanda
   ```

2. In `apps/api` create a Python 3.11 environment, install requirements,
   and configure **only local** connection strings:

   ```bash
   export DATABASE_URL='postgresql+asyncpg://sentinance:password@127.0.0.1:5432/sentinance'
   export KAFKA_BOOTSTRAP_SERVERS='127.0.0.1:19092'
   alembic upgrade head
   ```

3. From separate terminals in `apps/api`, using those same environment
   variables, start the consumer **before** publishing the fixtures:

   ```bash
   P1_DURABLE_PRICE_SINK_ENABLED=1 python durable_price_worker.py
   ```

   Then publish exactly two fixed, explicitly synthetic trades with
   **no external HTTP request**:

   ```bash
   P1_FIXTURE_SEED_ENABLED=1 python seed_market_fixture.py
   ```

   The fixture file is
   `apps/api/data/fixtures/synthetic_binance_aggtrades.json`.
   Running the command again republishes the same source IDs but should
   not produce extra rows.

4. Launch only the evidence API (this avoids launching real provider, Redis
   or LLM background tasks):

   ```bash
   uvicorn evidence_app:app --host 127.0.0.1 --port 8000
   curl 'http://127.0.0.1:8000/api/v1/market-events?symbol=BTCUSDT'
   ```

5. In `apps/web`, configure the **server-only** environment variable and
   start Next.js:

   ```bash
   SENTINANCE_API_URL=http://127.0.0.1:8000 npm run dev
   ```

   Visit `http://localhost:3000/data/evidence` and confirm two rows labeled
   **Synthetic fixture**. Disconnect the API and reload: the page must
   show the unavailable state instead of last-known/fake live quotes.

**Not verified by this recipe alone:** its runtime commands are
documented for a developer to reproduce; GitHub CI is the independent
execution evidence. The runner-backed integration test proves
fixture HTTP → real Kafka → real PostgreSQL → real ASGI query; frontend
schema/outage handling is separately tested by Vitest. A deployed
network browser-to-production API is still pending.

## Evidence acceptance gates

- [ ] Exact latest commit's API pytest, Ruff, MyPy, frontend
      Vitest/build/lint, dependency audit and security checks succeed.
- [ ] Real Kafka/Postgres job verifies successful FastAPI read after
      a fixture event is stored and confirms `live_feed_verified=false`.
- [ ] Frontend tests prove fixture mode, stale data, malformed API
      response, offline backend and no-data states.
- [ ] Human reviewer runs the commands above in an isolated environment,
      records a screenshot and links the verified deployment URL (if any).
- [ ] Parquet raw/validated/curated, late arrivals, backfill checkpoints,
      provider licensing, forecasting benchmarks and agent trace
      remain open P1–P4 milestones.

No automatic main merge, paid AWS provision, Terraform apply or real
exchange backfill is authorized by this test runbook.
