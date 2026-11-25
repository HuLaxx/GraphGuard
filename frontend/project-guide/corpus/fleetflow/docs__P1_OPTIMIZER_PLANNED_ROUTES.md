# FleetFlow P1 — Optimiser-generated planned dispatch

**Status: implementation proposed in draft PR; CI and full-stack integration evidence
must be checked on this branch head before this feature is called verified.**

This milestone makes a narrow, real part of the dispatch golden path possible:
**PostGIS orders/customers + available driver/vehicle → real OR-Tools solver →
persisted planned Route and RouteStop rows → existing dispatcher approval API**.

## Why the earlier path was misleading

Previously, `POST /api/v1/optimization/routes/optimize` could import a solver from
an uninstalled repository-level `ml` package. The optimiser expected latitude
and longitude on `Order`, although the actual ORM has them on `Customer`.
It also only returned transient route proposals. The new packaged solver lives
in `backend/src/optimization/route_optimizer.py`; historical ML smoke imports
use a thin compatibility wrapper, preventing separate solver implementations.

## Explicit operations

All requests require a running local backend, isolated PostGIS with seed data,
and the environment's appropriate authentication configuration.

1. Preview (read-only): `POST /api/v1/optimization/routes/optimize`.
2. Save proposals (dispatcher/admin token): `POST /api/v1/optimization/routes/plan`.
3. Inspect the created route IDs using `GET /api/v1/routes/{route_id}`.
4. Approve with `POST /api/v1/routes/{route_id}/approve` as dispatcher/admin.
5. Only an approved route may be started by an authorised assigned driver.

JSON input for preview and plan:

```json
{"depot_id": "REPLACE_WITH_SEEDED_DEPOT_UUID", "date": "2030-01-15"}
```

Plan creation is **not** approval, dispatch activation, route acceptance by a real
driver, or proof that GPS reaches the map. The plan endpoint holds row locks,
rejects overlapping active route/order assignments and commits all Route/Stop
rows together. The same order may not be silently planned twice while an active
plan exists. Historical/cancelled routes have separate lifecycle semantics.

## Data and solver constraints

- Customers supply actual demo-seed geocoordinates. Missing locations are
  rejected instead of silently substituting a zero-distance stop.
- Drivers must be assigned to available vehicles. Eligible orders must be
  pending at the selected depot and delivery date.
- Per-vehicle capacity is modelled in **grams** to avoid truncating fractional
  kilograms. The depot and order windows must fit one UTC route date.
- Route distance is a Haversine straight-line approximation, **not road
  mileage**. Illustrative travel time assumes 30 km/h. UI and README must not
  label these results as real-world observed distances or ETAs.
- OR-Tools returns feasible candidates under its encoded capacity and time
  constraints, not proven globally optimal routes.
- Before persistence, the API checks stop sequence, order coverage, driver,
  capacity and arrival windows. Approval is a separate API operation.
- Complete driver duty-hour constraints, live traffic, road restrictions and
  fuel/CO₂ optimisation are not implemented here.

## Acceptance test and checks

```bash
cd backend
python -m pip install -e ".[dev,lake]"
# Isolated local PostGIS test database, never production:
export DATABASE_URL="postgresql+asyncpg://fleetflow:fleetpass@localhost:5432/fleetflow_test"
# Provide a securely generated ephemeral JWT_SECRET_KEY in the test environment.
pytest tests/test_api/test_dispatch_planning.py -v
pytest --cov=src --cov-report=term-missing -v
ruff check src/
black --check src/
cd ..
python -m pytest ml/tests/test_core_ml_smoke.py -q
```

GitHub Actions additionally runs frontend lint/types/build and high/critical
dependency scanning. The acceptance cases cover read-only preview, solver
location correctness, persistence, explicit approval boundary, duplicate-plan
rejection, authorisation, unavailable vehicle, missing location and infeasible
capacity. Test evidence should be linked to the **exact matching head SHA**.

## Still not a complete end-to-end system

Kafka ingestion remains separate from this API transaction. There is no durable
transactional outbox or inbox, no actual Kafka-to-WebSocket browser smoke test,
and no reconciled dispatch mart or production cloud deployment. This is a
local-first milestone. **No AWS resources are provisioned.**

Next: immutable approval audit event, event outbox/inbox with replay tests,
driver/vehicle duty-hour validation, live UI telemetry and analytical
reconciliation, each with independent acceptance evidence.
