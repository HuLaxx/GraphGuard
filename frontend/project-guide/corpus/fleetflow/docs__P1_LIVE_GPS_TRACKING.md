# FleetFlow P1 — local live GPS tracking console

**Review status:** stacked draft PR #8 on PR #7; code CI and separate browser tests verified on commit `c27af41f38b4a14f535372465206249481d1a54d`. This integration is deliberately
**local-development only**. Public hosted telemetry is disabled until a
permission-scoped, authenticated WebSocket handshake and reviewed deployment
model exist. Do not call a Vercel build a live backend deployment.

## What is real

1. An authenticated driver with a linked `User.driver_id` sends
   `POST /api/v1/drivers/{driver_id}/location`. Admin and dispatcher roles
   can submit for controlled local testing. Invalid/foreign credentials fail.
2. The API writes `gps.location` into the **existing transactional
   PostgreSQL outbox**; HTTP **202 queued** means Kafka delivery is pending,
   not completed. No direct vehicle geolocation is falsely marked delivered.
3. Start the supervised outbox worker; it publishes using the real broker ACK
   and retries. The `GPSLocationConsumer` validates `event_id`, schema
   version 1, signed/offset-aware timestamp, finite geographic values and
   current vehicle/driver assignment. It updates the vehicle's PostGIS point,
   `last_gps_at`, `last_gps_event_id` and coordinates under row locking.
   It drops duplicate and older observed timestamps without broadcasting them.
4. The consumer uses the same in-process `ConnectionManager` as FastAPI's
   `/ws` endpoint, not a disconnected standalone process.
5. A local browser opens **`/tracking`**, subscribes to the `vehicles`
   channel and receives `vehicle_update`. On connection or reconnection,
   the server supplies up to 100 actual last-known vehicle positions from
   PostGIS in `vehicle_snapshot`.
6. Frontend validates UUIDs, coordinate ranges, timestamps and event time,
   never rewinds positions on delayed/snapshot updates, retries with capped
   exponential backoff and marks data **stale after 60 seconds** or **offline**
   when the socket is disconnected. A socket being connected is not itself
   proof of fresh telemetry.

## Local-only boundaries and security

- Set `ENVIRONMENT=development` on the API only for trusted local work and
  use an Origin in `WEBSOCKET_ALLOWED_ORIGINS`, default localhost:3000/3001
  or 127.0.0.1:3000. An arbitrary Origin is rejected; non-development
  WebSocket sessions are rejected. Browser clients cannot see positions
  without explicitly subscribing to `vehicles`.
- The unauthenticated live WebSocket is **not production-safe**, even with an
  Origin check. Do **not expose the development WebSocket service to the
  public internet**. An authenticated socket handshake, per-role depot
  permissions, rate limiting and deployment isolation are release blockers.
- The HTTP broadcast endpoint is **disabled** unless
  `WEBSOCKET_BROADCAST_TOKEN` is explicitly configured. The standalone
  WebSocket module no longer starts sample GPS broadcasts. Kafka and browser
  live updates run inside the shared FastAPI process, not in two separate
  in-memory servers. Multi-instance deployment needs Redis/NATS pubsub.
- The public `/demo` still shows **seeded demonstration** vehicles/routes;
  it must not be represented as live. `/tracking` never generates a random
  sample vehicle. In hosted environments without `NEXT_PUBLIC_WS_URL`,
  the browser displays *Not configured*, never a fabricated LIVE badge.
- GPS data collection should use consent and access controls in any real
  fleet. There is currently no driver-location history retention policy or
  multi-tenant isolation.

## Reproducibility

Apply additive migration `db/init/05_gps_tracking.sql` **after** 03 and 04
on an approved local database, or initialize a fresh PostGIS database from
the repository's migration chain. Do not run against production without a
reviewed migration plan.

Start local PostGIS, broker, backend and outbox worker in separate terminals.
For example with environment correctly configured:

```bash
cd backend
python -m pip install -e ".[dev,lake]"
# Backend serves HTTP /api/v1 and WebSocket /ws on the same port.
uvicorn src.main:app --host 127.0.0.1 --port 8000
# In another terminal:
python -m src.reliability.worker --forever --interval 2
# Frontend (another terminal):
cd ../frontend
pnpm install --frozen-lockfile
pnpm dev
# Visit http://localhost:3000/tracking
```

A dispatcher/driver JWT must be obtained from the existing login path. The
authenticated GPS POST returns an event ID and `delivery_status=pending`.
Once the outbox worker publishes it and the subscribed GPS consumer has
committed the position, `/tracking` can show the fresh vehicle. Without the
worker or Kafka, the tracking console will show no data or stale data.

## Verified CI results

- [Backend run 43688456913](https://github.com/HuLaxx/FleetFlow/actions/runs/43688456913), **5/5 jobs successful** on code SHA `c27af41f38b4a14f535372465206249481d1a54d`: **91 backend tests passed, 2 intentionally skipped broker-only tests, 3 warnings, 65% backend statement coverage**. Ruff, Black, frontend lint/types/build, CPU ML smoke and high/critical security checks all passed.
- [Chromium run 43688456894](https://github.com/HuLaxx/FleetFlow/actions/runs/43688456894), same code SHA: **3 Playwright live-tracking tests passed, with no retries**. Validated GPS movement, late-packet rejection, resubscription after reconnect, stale position badge, and zero fabricated vehicles. Test broker messages are **stubbed** in this browser workflow.
- [Real Kafka + PostGIS run 43688250065](https://github.com/HuLaxx/FleetFlow/actions/runs/43688250065), previous backend-identical code SHA `febef2d2c8bdfd1e1f15423b7c30fcf7fb241409`: **both actual Redpanda broker tests and 5 focused poison/offset tests passed**, including newly added GPS broker-to-PostGIS-to-WebSocket manager delivery and duplicate-on-restart suppression. Subsequent commits modified frontend components/browser tests only; the broker-tested backend sources did not change. This test intentionally uses a mocked WS manager, not a real browser.
- Earlier failing checks identified and fixed map camera/fallback handling, a stale browser mock socket, unused imports/formatting and a Playwright Next.js startup command. These failure modes remain in review history; do not count any failed/cancelled runs as passing.
- Documentation-only commits after these code checks require an independent matching HEAD check. These results do **not** demonstrate a deployed internet-facing live tracking service.

## Acceptance evidence

- PostgreSQL tests cover driver identity enforcement, queued outbox without
  premature DB movement, actual PostGIS position update, duplicate and late
  event suppression, invalid GPS and mismatch rejection, WebSocket
  subscriptions/snapshots, and local Origin policy.
- Browser Playwright tests intercept the WebSocket **with controlled fixture
  packets** to validate stale, reconnect, marker and no-fake-state UX. They
  are not proof of a real browser connected to a real broker.
- Separate PR #7 proof already verified Redpanda producer ACK, inbox
  deduplication, crash-window replay and durable message quarantine. This
  PR does not yet prove an automated **browser → real Redpanda → real API**
  full-stack journey. Link exact CI/head evidence only after runs pass.

## Still outstanding

Full stack process/network fault injection, actual GPS history in TimescaleDB,
authenticated remote multi-tenant socket subscriptions, multi-worker WebSocket
fanout, broker-to-browser latency measurement, WebSocket notification
reconciliation, operational alerts, location privacy/retention controls,
production hosting and a real browser connected to real services in one
verified acceptance run. No AWS resources are created.
