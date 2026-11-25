# FleetFlow P2 — reproducible synthetic route-planning baseline evaluation

[Draft PR #11](https://github.com/HuLaxx/FleetFlow/pull/11) stacks on
[draft PR #10](https://github.com/HuLaxx/FleetFlow/pull/10).

## Question

On the same deliberately small synthetic logistics fixtures, how does
**real OR-Tools CVRPTW** differ from two simple but capacity- and
time-window-aware baselines?

The evaluators are **input-order assignment** and **nearest feasible
neighbour**. All three methods are independently checked for weight
capacity, service time, UTC windows, depot return and unassigned orders.
No algorithm gets credit for short distance by dropping an order.

## Fixtures and limitations

`backend/src/optimization/heuristic_baselines.py` specifies fixed synthetic
vehicle IDs, depot/driver IDs, customer coordinates and order windows
for `city_feasible`, `window_feasible` and `capacity_infeasible`.
This is not a model training/held-out-accuracy experiment: a routing
solver is not trained on these orders. No addresses are real.

The comparison uses **rounded Haversine straight-line metres** with a
**constant illustrative 30 km/h** speed. Service time is five minutes
per stop and all windows fall on a fixed UTC route date. This is **not**
a road-network, live traffic, fuel or ETA benchmark.

An illustrative planning-cost sensitivity calculation is explicitly
`£0.35/km + £12/hour`. These values are chosen assumptions, **not**
actual employee wages, fuel costs, verified operating expenses or
savings. Cost is `null` whenever a route set has unassigned orders
or violates a constraint. Optimizer solve times are measured inside
each CI runner and are machine-specific; compare with those caveats.

Input-order and nearest-neighbour baseline schedules depart at the
depot's fixed opening time; the OR-Tools planner may choose another
feasible start within the same window. The reported aggregate
scheduled duration includes waiting, not just driving. Objective
comparison should primarily evaluate service coverage, feasibility
and distance and should not treat illustrative cost as an economic win.

## Reproduction

```bash
python -m pip install -e './backend[dev]'
python -m pytest backend/tests/test_optimization/test_heuristic_baselines.py -q
python -m src.optimization.heuristic_baselines \
  --solver-seconds 1 \
  --output /tmp/fleetflow-route-baseline.json
python -m json.tool /tmp/fleetflow-route-baseline.json
```

For every scenario/method the output includes `served`, `orders`,
`unassigned`, `constraint_violations`,
`total_distance_km`, `total_duration_minutes`,
`solve_time_ms`, `illustrative_cost_gbp` and
`is_feasible`. CI stores the JSON as a downloadable workflow artifact,
and prints each per-scenario result in job logs.

## Evidence

- [Real evaluation run 44107553076](https://github.com/HuLaxx/FleetFlow/actions/runs/44107553076)
  on SHA `1f311b5f7818e0b8e997b6a4a5d7926dee4d7b96`:
  one actual OR-Tools runtime job passed, 4 benchmark acceptance
  tests passed, **3 scenarios × 3 methods**, **5 fully feasible
  combinations**; infeasible combinations had NULL cost, as verified
  by the machine-readable artifact check. This is synthetic local
  evidence only.
- A later code-only Black formatting correction and CI log expansion
  require independent exact-HEAD checks. Do not cite the earlier run
  as final-HEAD green without verifying the latest commit.

## Not yet established

No real route-distance uplift, fuel savings, live ETA, traffic data,
road OSRM results, statistical confidence/uncertainty on real fleet
distributions, sustained load, cloud spend or production deployment.
The optimizer's 1-second time budget is a benchmark fixture setting,
not a statement about production SLA.
