# Local Readiness Standard (Strict)

This document defines what **100% local readiness** means for FleetFlow. Passing all gates below is required for "local ready" status.

## Summary Gates (All Must Pass)
1. **One-command bootstrap**: full stack starts and passes health checks.
2. **Deterministic data**: seed + replay steps produce the same results each run.
3. **Training pipeline**: ML training runs end-to-end with logged metrics.
4. **Rigorous tests**: unit + integration + e2e + smoke checks are green.
5. **Code quality**: linting, formatting, typing are clean.
6. **Observability**: metrics and dashboards are accessible locally.

---

## Gate 1: One-command Bootstrap
- Command: `scripts/dev-up.ps1` or `scripts/dev-up.sh`
- `scripts/run-local.*` auto-creates `backend/.venv` with Python 3.11 and installs backend deps if missing.
- Required services reachable (ports from `.env.ports`):
  - API: http://localhost:8000/health
  - WebSocket: http://localhost:8002/health
  - Kafka UI: http://localhost:8080
  - Airflow: http://localhost:8081
  - Flink UI: http://localhost:8082
  - MLflow: http://localhost:5001
  - OSRM: http://localhost:5000 (profile `routing`)

**Pass**: all endpoints respond with HTTP 200.

OSRM bootstrap (required once):
- `scripts/osrm-bootstrap.ps1` or `./scripts/osrm-bootstrap.sh`

---

## Gate 2: Deterministic Data
- DB seed script generates consistent drivers, orders, routes.
- Kafka replay script produces stable event counts.

**Pass**: same seed inputs => same row counts and event totals.

Commands:
- `scripts/seed-db.ps1 --reset` or `./scripts/seed-db.sh --reset`
- `scripts/replay-kafka.ps1` or `./scripts/replay-kafka.sh`

---

## Gate 3: Training Pipeline
- Synthetic data generation is deterministic.
- Training pipeline runs with logged metrics (MLflow).
- Model artifact is saved with version metadata.

**Pass**: training completes without error and produces metrics + artifact.

Command:
```
python ml/training/train_forecaster.py --seed 42
```
Quick command:
- `scripts/train-forecast.ps1` or `./scripts/train-forecast.sh`
Outputs:
- `ml/training/metrics/metrics_seed42_<hash>.json`
Optional envs:
- `MLFLOW_TRACKING_URI=http://localhost:5001`
- `MLFLOW_EXPERIMENT=demand_forecasting_rigorous`
- `ML_METRICS_DIR=ml/training/metrics`

---

## Gate 4: Rigorous Tests
- Backend: `pytest --cov=src --cov-fail-under=85`
- Frontend: `pnpm lint` + `pnpm test:e2e`
- API smoke tests for RAG, health, and critical endpoints.
- ML: `pytest -m "not slow"` (slow training test optional)

**Pass**: all tests green, coverage threshold met.

---

## Gate 5: Code Quality
- Backend: `ruff`, `black --check`, `mypy` clean
- Frontend: ESLint clean, TypeScript clean

**Pass**: zero warnings/errors.

---

## Gate 6: Observability
- Prometheus scrapes metrics
- Grafana dashboards load without errors

**Pass**: dashboards visible and populated.

---

## Local Readiness Checklist (Working)
- [x] OSRM bootstrap script implemented
- [x] DB seed script implemented
- [x] Kafka replay script implemented
- [x] Training script deterministic + documented
- [x] Validation script runs all gates

---

## Recommended Validation Command
- `scripts/validate-local.ps1` (Windows)
- `scripts/validate-local.sh` (macOS/Linux)

Optional flags:
- `--skip-ml` to skip ML unit tests
- `--skip-ml-training` to skip training smoke run
