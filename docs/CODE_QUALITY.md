# GraphGuard - Code Quality Notes (Evidence-based)

This is a lightweight, evidence-first snapshot based on the current repo. It does not assert production readiness.

## Observed strengths
- Pydantic request/response models and input validation in `ml/serving/api.py`.
- Modular organization for data engineering, ML training, serving, and frontend.
- Structured logging (structlog) across key services.
- Local stack defined via Docker Compose for reproducible demos.

## Known gaps / placeholders
- GAT scoring in the API is stubbed (see `gat_score = None`).
- Retraining pipeline is a template, not wired end-to-end.
- Terraform exists as a template and has not been validated in this repo.

## Testing status (evidence)
- Python tests: `docs/evidence/python-tests-*.txt`
- Python coverage (RAG): `docs/evidence/python-coverage-*.txt` and `docs/evidence/coverage/rag/`
- Frontend tests: `docs/evidence/frontend-tests-*.txt` and `docs/evidence/coverage/frontend/`

## Security notes
- API keys and secrets are sourced from environment variables.
- Rate limiting middleware exists but is opt-in via `ENABLE_RATE_LIMITING`.

## Recommended next steps
- Document expected alert thresholds and add dashboard screenshots.
- Wire GAT scoring into the serving path or document as future work.
- Add integration/e2e tests for critical flows.
