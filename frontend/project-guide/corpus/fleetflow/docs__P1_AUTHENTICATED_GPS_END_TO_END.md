# FleetFlow P1 — authenticated GPS stream and non-mocked full-stack proof

**Review:** [draft PR #9](https://github.com/HuLaxx/FleetFlow/pull/9), based on
[draft PR #8](https://github.com/HuLaxx/FleetFlow/pull/8). Neither branch has
been merged to `main`, publicly deployed or used to provision AWS.

## Data-protection contract

- A browser sends an **access** JWT only as the **first WebSocket frame**
  `{"action":"authenticate","token":"<access-token>"}`, within five seconds.
  Never send a JWT in a URL, cookie or subprotocol. The server explicitly
  rejects refresh tokens, bad signatures, expired tokens, unknown/deactivated
  users, stale JWT roles, viewers and identities without explicit scope.
- No implicit subscription exists. Only the `vehicles` channel is supported.
  A successful `authenticated` frame permits a `subscribe` request; a
  `subscribed` acknowledgement gates the browser's connected status.
- A **driver** sees only vehicles currently assigned to their linked
  `User.driver_id`. A **dispatcher** sees vehicles in their explicitly
  assigned `User.depot_id`; NULL grants no access. An **administrator** may
  see the full local test fleet. An anonymous user or viewer has **no GPS
  access**. Scope is loaded from PostgreSQL, not trusted from JWT claims.
- PostGIS snapshots on subscribe/reconnect are filtered by current scope.
  Every Kafka-to-WebSocket broadcast rechecks the DB identity, role, depot,
  driver assignment and access-token expiry. Revocation closes the socket.
  Message/snapshot fields do not embed credentials.
- REST `GET /api/v1/vehicles/{id}/location` requires a signed-in, scoped
  user; unscoped vehicle/driver listings redact location fields. GPS write
  `POST /api/v1/drivers/{id}/location` rejects unlinked drivers and
  dispatchers without a matching depot.
- New passwords are Argon2id, existing bcrypt hashes are verified through
  the supported bcrypt package. Refresh JWTs are accepted only at the
  explicit refresh endpoint. UTC login timestamps match the existing naive
  PostgreSQL timestamp column.

**Privacy boundary:** These protections are validated for a **single-process
local development** topology. `ENVIRONMENT!=development` still disables
WebSocket handshakes; this PR does **not** grant permission for public
production streaming. Strong TLS termination, rate limiting, user/device
revocation semantics, multi-instance broadcast fanout, historical retention
controls, encryption/observability review and externally hosted deployment
remain open gates.

## Non-mocked acceptance

CI file: `.github/workflows/gps-full-stack.yml`.

1. Provision disposable PostGIS and Redpanda containers on a hosted CI
   runner, with a guarded **local** `fleetflow_test` database.
2. Initialize the ORM schema and exercise additive migrations
   `03_dispatch_reliability.sql` through
   `06_websocket_dispatch_scope.sql`; no production database touched.
3. Generate temporary JWT signing secret and password in the runner;
   seed a synthetic depot, driver, vehicle, Argon2id user. No real driver
   location, customer records or external credentials.
4. Start FastAPI and the supervised local outbox worker. Wait for the
   GPS consumer's Kafka group assignment before publishing.
5. Open Chromium **without routeWebSocket or HTTP intercepts**. Log in via
   the real FastAPI endpoint; wait for authenticated GPS subscription.
6. Submit a real driver GPS update, assert the API says `202 queued`;
   the outbox worker publishes to real Redpanda; the consumer commits a
   PostGIS coordinate and sends a scoped `vehicle_update`. Assert the
   browser displays the exact latitude/longitude, Kafka event source and
   fresh state. Independently query the scoped DB-backed REST endpoint.
7. Verify unauthenticated GPS REST returns 401; sign out and verify browser
   state is cleared. Tear down the disposable broker and processes.

The Chromium acceptance proves **one end-to-end synthetic local sample**.
It does not measure p95 latency, multi-driver throughput, sustained load,
production uptime, cross-region replay or multi-worker live fanout.

## Inspectable evidence

- [Full-stack CI run 43926162453](https://github.com/HuLaxx/FleetFlow/actions/runs/43926162453)
  on code SHA `242d42888f5eea86bac460c5ad629525d29106c8`:
  **1 actual, non-mocked Chromium/Redpanda/PostGIS test passed**.
  The first attempts correctly caught a Passlib-bcrypt incompatibility and
  naive/aware timestamp mismatch, both fixed with regression tests.
- [Backend CI run 43926162615](https://github.com/HuLaxx/FleetFlow/actions/runs/43926162615)
  on same SHA: **101 passed, 2 deliberately broker-only skips,
  2 warnings, 67% coverage**, frontend lint/types/build, ML CPU and
  dependency security succeeded; Python lint had an **import-order** failure.
  That run is not five-job green.
- [Kafka CI run 43926162472](https://github.com/HuLaxx/FleetFlow/actions/runs/43926162472)
  on same SHA: two real-broker tests plus five focused tests passed.
- [Browser mocked-contract run 43926162482](https://github.com/HuLaxx/FleetFlow/actions/runs/43926162482)
  on same SHA: four pass, including sign-in/subscription, stale/reconnect,
  no fabricated vehicles and permission denial.
- A subsequent code-only import-order/format fix has been committed.
  Record its **exact HEAD** CI separately; do not extrapolate earlier run
  success. Browser/mock suites and full-stack suite are independent.

## Next engineering gates

PostGIS-backed GPS history / consent-aware retention; multi-instance socket
fanout; secure TLS-authenticated production deployment with session
revocation/rate limits; Redis/NATS external pubsub, typed historical
position contracts, Kafka/WS backpressure and lag alerts; a full
network-fault injection suite; reproducible latency and throughput
benchmarks; P2 Parquet/dbt/Airflow reconciliation and forecasting baselines.
