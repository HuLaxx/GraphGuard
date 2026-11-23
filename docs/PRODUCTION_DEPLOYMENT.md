# GraphGuard Deployment Notes (Portfolio)

This repository is optimized for local development and demo use. The only supported, repeatable setup today is the local Docker Compose stack.

## Local deployment (supported)

Prereqs:
- Docker + Docker Compose
- Python 3.10+
- Node.js 18+

Steps:
1) `cp .env.example .env`
2) `docker-compose up -d`
3) `python -m uvicorn ml.serving.api:app --reload --port 8000`
4) `cd frontend && npm install && npm run dev`

## Terraform (template only; safe isolated review module now available)

- `infrastructure/terraform/main.tf` remains an **unvalidated, high-cost historical template** with EKS/NAT/MSK/RDS and must **not** be run by default.\n- `infrastructure/terraform/research/` defines a separate cost-aware private S3/Glue/Athena/OIDC **review-only** root, offline validation via P4 workflow; no AWS apply or plan is done.
- Treat it as a starting point, not a production-ready configuration.

## Production plan (not implemented in this repo)

The following items are **planned** for a hosted demo but are not wired up here:
- Managed services (Supabase, Upstash, Railway) for the hosted demo stack.
- Kubernetes/Helm manifests (none exist under `infrastructure/`).
- Container image build/push scripts (no Dockerfiles are included).
- Load testing targets and SLA numbers (no verified benchmarks yet).

If you deploy this project, document the environment, configs, and performance results in `docs/evidence/` so claims are verifiable.
