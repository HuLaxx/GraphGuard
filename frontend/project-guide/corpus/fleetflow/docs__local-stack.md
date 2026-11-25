# Local Full-Power Stack

FleetFlow is portfolio-first and local-first. The live demo is constrained to free-tier deploys, but the local stack is where full capability is shown.

## Quick Start

```bash
# One command: infra + backend + frontend
# Windows
scripts\run-local.ps1

# macOS/Linux
./scripts/run-local.sh

# Infra only
# Windows
scripts\dev-up.ps1

# macOS/Linux
./scripts/dev-up.sh
```

## OSRM Bootstrap (Required for Routing Profile)

```bash
# Windows
scripts\osrm-bootstrap.ps1

# macOS/Linux
./scripts/osrm-bootstrap.sh
```

The OSRM service expects a `.osrm` dataset inside the `osrm_data` Docker volume.

## Compose Profiles
- `data`: Airflow + Flink
- `ml`: MLflow
- `routing`: OSRM

Example:
```bash
docker compose --profile data --profile ml --profile routing up -d
```

## Services and Ports
Ports are auto-selected and written to `.env.ports`. Defaults (if free):
- API (FastAPI): http://localhost:8000
- WebSocket: http://localhost:8002
- Kafka UI: http://localhost:8080
- Airflow UI: http://localhost:8081
- Flink UI: http://localhost:8082
- MLflow UI: http://localhost:5001
- OSRM: http://localhost:5000 (profile `routing`)

To regenerate ports:
```bash
scripts\ports-auto.ps1 -Force
./scripts/ports-auto.sh --force
```

## Notes
- Airflow uses a local SQLite DB for quick-start (`airflow standalone`).
- Flink job binaries can be mounted via `data-engineering/flink`.
- MLflow artifacts are stored in a Docker volume (`mlflow_data`).
- ML training metrics summary files are stored in `ml/training/metrics/` (gitignored).
- OSRM requires a built `.osrm` dataset in the `osrm_data` volume.
- `scripts/run-local.*` will create `backend/.venv` with Python 3.11 and install backend deps if missing.
- Seed data: `scripts/seed-db.ps1 --reset` (Windows) or `./scripts/seed-db.sh --reset` (Linux/macOS).
- Kafka replay: `scripts/replay-kafka.ps1` or `./scripts/replay-kafka.sh`.
- OSRM envs (optional): `OSRM_PBF_URL` and `OSRM_DATASET` in `.env`.
- ML training quick run: `scripts/train-forecast.ps1` or `./scripts/train-forecast.sh`.
