# FleetFlow P1 — approval audit, transactional outbox and inbox

**Review status:** New draft implementation. This is local-first application code,
not a live Kafka integration test or proof of a production service.

## Reliability contract

1. Dispatcher approves an already-persisted, validated planned route.
2. The same PostgreSQL transaction writes the approved route state, one
   `route_approval_audit` row (authenticated actor UUID, timestamp, status
   transition and event ID), and one pending `dispatch_outbox` row.
3. A separate worker selects due outbox rows with `FOR UPDATE SKIP LOCKED`,
   publishes to the `routes.approved` topic and **waits for a delivery ACK**.
   Only confirmed deliveries are marked `published`; timeouts/NACKs remain
   pending with bounded exponential backoff.
4. The `RouteEventsConsumer` validates the receipt against both the real
   approved route and matching audit row, then inserts an inbox receipt under
   unique `(consumer_name, event_id)`. Its enclosing DB transaction commits
   after verification, before the Kafka offset is acknowledged.
5. A repeated event with the same ID has no second inbox side effect.

This implements **at-least-once** delivery with transactional DB deduplication.
A crash after Kafka ACK but before the DB's `published` commit may send the
event again. The consumer must use `event_id` rather than assuming exactly
once. External side effects such as WebSocket pushes are NOT atomically covered
by the inbox receipt; do not call this end-to-end exactly-once delivery.

## Database setup is explicit

A new SQL file `db/init/03_dispatch_reliability.sql` adds the three tables,
indexes, route approval status and database trigger protecting audit rows from
UPDATE or DELETE. On a fresh database where `db/init` scripts are applied
in sequence, it runs after `01_postgis_schema.sql`. Existing databases must
apply it explicitly, in a reviewed, approved maintenance window:

```bash
# EXAMPLE ONLY; adjust connection/permissions, no production run by ChatGPT
psql "$DATABASE_URL_FOR_PSQL" -v ON_ERROR_STOP=1 -1 \
  -f db/init/03_dispatch_reliability.sql
```

`DATABASE_URL_FOR_PSQL` must be a **psql-compatible** Postgres URI, not the
asyncpg SQLAlchemy URL. No tables are dropped and no user records are copied.
The script recreates the same audit trigger when re-applied.

The ORM test suite creates these tables via SQLAlchemy metadata in isolated
`fleetflow_test`, but the append-only *database trigger* is supplied by the
explicit SQL migration, not by `create_all`. The trigger regression test
installs the identical trigger on its isolated test transaction and verifies
UPDATE and DELETE fail. Test schema setup is not a production migration.

## Run the worker (explicit opt-in)

```bash
cd backend
python -m pip install -e ".[dev,lake]"
# Set a configured PostgreSQL URL and Kafka brokers in the environment.
python -m src.reliability.worker --once
# Only under process supervision + alerting:
python -m src.reliability.worker --forever --interval 2
```

There is **no implicit publish daemon** hidden inside FastAPI startup. A
successful API response reports `delivery_status=pending`, not `delivered`.
Worker process health, backlogs, dead letters, retention, telemetry and
resilience at sustained load need further verification.

## Independent acceptance tests

```bash
cd backend
# CI uses only local PostGIS fleetflow_test with JWT_SECRET_KEY set.
pytest tests/test_api/test_dispatch_reliability.py -v
pytest tests/test_unit/test_outbox_ack.py -v
pytest --cov=src --cov-report=term-missing -v
ruff check src/
black --check src/
```

Test assertions cover:

- One audit row + one pending event from one role-gated approval.
- A repeated approval returns a conflict and does not add another event.
- A simulated Kafka timeout leaves the event pending and schedules retry.
- A later simulated ACK publishes that same event ID.
- Inbox deduplication of redelivered IDs, and rollback on handler failure.
- Real Postgres trigger rejects UPDATE and DELETE on approval audit rows.
- A fake Kafka producer's ACK/NACK/timeout callbacks, not an actual broker.

## Intentional limits and next step

Not yet evidenced: broker-backed restart/replay with actual Kafka, a
transactional outbox for all other route/order events, duplicate-safe
WebSocket notification, DLQ/poison-event policy, operational backlog alarms,
24-hour event-time corner cases, deployed AWS/Vercel backend and full
source→Kafka→dispatch→GPS→analytics demo. No AWS resources were provisioned.
