# Assessment Remediation Tracker

This file tracks fixes for the assessment gaps (evidence, security, CI, docs).

## Priority 1 — Security Hygiene
- [x] Remove committed `.env` and keep only `.env.example`.
- [x] Replace hardcoded API keys in `test_api_client.py` and `streaming_consumer.py` with env vars.
- [ ] Rotate dev keys (regenerate local secrets as needed).

## Priority 2 — CI + Tests + Evidence
- [x] Remove `continue-on-error` from CI.
- [x] Fix frontend test job with Vitest.
- [x] Add coverage report (`pytest --cov`) and store HTML output.
- [x] Save test output logs under `docs/evidence/`.

## Priority 3 — Docs Accuracy
- [x] Align README + backend/infra/frontend docs with actual entrypoints.
- [x] Remove or qualify claims that lack proof.

## Priority 4 — Observability Wiring
- [x] Implement real `/metrics` using `ml/monitoring/performance_monitoring.py`.
- [x] Add evidence (screenshot/log) that metrics are exported.

## Priority 5 — API Consolidation
- [ ] Choose canonical API (either `ml/serving/api.py` or `api_production.py`).
- [ ] Update docs accordingly.

## Priority 6 — Infra Proof
- [x] Provide `docker-compose up` proof (output/logs).
- [ ] Document minimal hardware requirements.
