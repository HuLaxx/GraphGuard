# GraphGuard P3 — Same-source Kafka-to-Chromium and bounded local latency

**Scope:** synthetic-only, reproducible, actual disposable test services. No real payments, real fraud outcomes, production OIDC, cloud deployment, or paid infrastructure. This is a development acceptance gate, not evidence of a production bank system.

## New: one continuous source-to-browser test

The test `test_uninterrupted_registered_avro_to_real_chromium_case` in `tests/integration/test_avro_registry.py` is opt-in with `GRAPHGUARD_INGESTION_INTEGRATION=1` and `GRAPHGUARD_BROKER_CHROMIUM=1`. The workflow job `unified-broker-chromium` starts Kafka, Schema Registry, Neo4j, signed local Python API, Next.js and **real headless Chromium in the same ephemeral CI runner**.

It must prove, on **one accepted transaction ID**:

1. Production-shaped `TransactionProducer` Avro bytes registered with the running Confluent Schema Registry and delivered via real Kafka; no direct-ledger substitution.
2. `GraphBuilder` validates that source, saves its first-receipt ledger record and immutable `pit-v1` feature snapshot, and projects the exact transaction into Neo4j with source SHA.
3. A synthetic XGBoost/logistic baseline trained separately with a pinned SHA-256 manifest actually scores that accepted source; real native SHAP reconstructs the same model probability.
4. A case is anchored to source/feature/model/SHAP hashes with a real short-lived **local signed demo** analyst token. No API route mints production credentials.
5. Next's real signed local proxy, actual Chromium page and actual FastAPI reject an invalid token, let the analyst inspect all 12 numeric SHAP features, escalate, then authenticate a distinct demo admin to close the case.
6. The browser reports the identical transaction ID and original source/model/SHAP hashes, a terminal `CLOSED_REVIEW_COMPLETE` case and 3 signed append-only review events. The separate GraphBuilder replay reuses real broker bytes and verifies case integrity remains unchanged.

**Important distinction:** previous PR #14 Chromium accepted a *direct-seeded* SQLite fixture and PR #13 separately covered broker→case in TestClient. This unified test checks the **same original broker event in the real browser**, with two source integrity observations. A local single-node synthetic proof does not replace authorization, external audit anchoring or production reliability validation.

Command with local prerequisites installed and docker compose running:

```bash
GRAPHGUARD_INGESTION_INTEGRATION=1 \
GRAPHGUARD_BROKER_CHROMIUM=1 \
python -m pytest \
  tests/integration/test_avro_registry.py::test_uninterrupted_registered_avro_to_real_chromium_case -v
```

Expected sanitized artifacts (after a successful job): `synthetic-review-proof.json`, screenshot `synthetic-review-final.png`. No bearer tokens or signing secrets may appear in either output. The artifact is retained 14 days.

## New: bounded local p50/p95 reproducibility

`ml/review/benchmark_local.py` drives **24 total requests** on the signed development-only Next→FastAPI proxy, two concurrent workers, half reading the anchored synthetic case and half re-running and checking real native SHAP. It verifies every response’s original model/source/explanation hashes and outputs per-route nearest-rank p50/p95 in milliseconds plus failures.

```bash
python -m ml.review.run_local_demo \
  --workspace .local/graphguard-benchmark \
  --benchmark \
  --evidence-dir .local/graphguard-benchmark-results
```

CI job `signed-local-latency` runs the benchmark, tests the stats function and uploads the synthetic `synthetic-latency.json` for 14 days. The benchmark warms Next and the first SHAP call before measuring. The timing numbers reflect an **ephemeral GitHub runner**, not a stable benchmark host. They are a descriptive baseline, **not** a production p95 SLO, load test, capacity planning proof or cloud-service measurement.

## Security/evidence gates

- All source transactions and reviewer credentials are generated synthetically on disposable CI; no real customer/finance data.
- Both Next and FastAPI bind to 127.0.0.1; endpoint allowlist and signed bearer identity remain enforced. Tests do not expose a hosted production backend.
- Exact source/model/feature/SHAP hashes must match on both sides of the reviewer UI. A real browser is not proof that a model prediction is a genuine fraud signal.
- Do not check the new acceptance boxes in the release checklist or increase the scorecard until the **current implementation commit** has green CI and inspectable artifacts.
- Remaining production release blockers include licensed external data, independent cold-start evaluation, enterprise OIDC/MFA and revoked keys, external signed audit anchoring, calibrated model deployment/rollback, measured production SLAs, approved AWS apply/teardown and main-branch review/merge.
