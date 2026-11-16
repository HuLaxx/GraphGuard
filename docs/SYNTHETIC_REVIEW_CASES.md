# GraphGuard P1 — Signed local analyst case review and audit

**Scope:** a genuinely executable **local, synthetic-only** review workflow. This is **not a production identity provider, regulatory case-management system, deployed service or automated fraud decision**. No real user, payment or bank case is supported.

## Tested golden path

1. A synthetic registered Avro event is published to disposable Kafka/Schema Registry and materialized by `GraphBuilder` into Neo4j and a durable local SQLite ledger.
2. The independent manifest-SHA-pinned scorer verifies the accepted source, model and first-seen `pit-v1` feature snapshot and computes a trained-model research probability.
3. Real native TreeSHAP / analytic linear Shapley attribution is computed, reconstructs the verified score, and is persisted with its exact SHA-256 and model/source/feature provenance.
4. **Only a short-lived signed demo reviewer token** permits case creation, reading and review actions. The HTTP application neither exposes token issuance nor accepts reviewer ID or role from body JSON.
5. Case creation rechecks source, model and explanation and anchors the case to those same hashes. A case ID is deterministic for a `(transaction ID, trusted manifest)` pair. Idempotent retries must use the original reviewer and request ID.
6. Review actions are restricted to a finite state machine. A demo analyst may `request_more_information` or `escalate`; a distinct demo admin is required to close a case. Closed cases cannot be reopened or silently changed. All writes require an explicit request ID and expected version (optimistic conflict protection).
7. Review events are **insert-only** SQLite records, and case status is derived from the ordered events. Each event includes actor ID/role/token ID (not token bytes), event time, prior-event hash, SHA-256 and a separate **HMAC-SHA256** using the local audit key. SQLite triggers block updates/deletes; reads and actions validate sequence, signatures and legal state transitions.
8. Replay via a fresh Kafka consumer group reproduces the same score/SHAP and unchanged terminal case history; test fixtures assert no duplicate events.

## Running the local HTTP service (Python 3.11)

```bash
python -m pip install -r requirements-review-ci.txt
python -m pytest tests/unit/test_synthetic_review.py -v
python -m pytest tests/unit/test_pit_baselines.py \
  tests/unit/test_verified_pit_scorer.py \
  tests/unit/test_verified_shap.py \
  tests/unit/test_synthetic_review.py -v
```

First train the synthetic model and ingest a synthetic transaction using the earlier steps in `docs/SYNTHETIC_BASELINES.md` and `docs/AVRO_INGESTION.md`. Obtain its model-manifest digest from an **independent trusted CI/build source**, not from a candidate untrusted model folder.

Inject **two independent cryptographically random secrets of at least 32 bytes** into a local secret store/environment. Do not commit secrets or bearer tokens. Required configuration:

- `GRAPHGUARD_DEMO_REVIEW_KEY`: reviewer token HMAC signing secret, distinct from audit key
- `GRAPHGUARD_DEMO_AUDIT_KEY`: review event HMAC secret, distinct from token key
- `GRAPHGUARD_LEDGER_PATH`: existing local synthetic transaction ledger SQLite path
- `GRAPHGUARD_MODEL_DIR`: trusted training artifact directory
- `GRAPHGUARD_TRUSTED_MANIFEST_SHA256`: independently trusted 64-char model-manifest SHA-256

```bash
python -m ml.review.serve_local
```

This explicitly binds Uvicorn to **127.0.0.1:8765**, disables access logging and fails closed if required secrets or artifacts are missing. No CORS allowlist for remote browsers is enabled. There is no public deployment.

Mint demo reviewer tokens offline on the same trusted operator machine (never from an API route):

```bash
python -m ml.review.mint_local_token --subject analyst.one --role analyst --ttl-seconds 600
python -m ml.review.mint_local_token --subject admin.one --role admin --ttl-seconds 600
```

Keep token strings out of issue comments and screenshots. Pass each token in an `Authorization: Bearer <token>` header to the **local-only** POST `/cases`, GET `/cases/{case_id}`, POST `/cases/{case_id}/actions`. The OpenAPI schema lists request bodies; malformed fields and unapproved actions fail.

Example request bodies (not actual tokens or identities):

```json
{"transaction_id":"synthetic-example","request_id":"create-req-0001"}
```

```json
{"action":"escalate","request_id":"review-req-0001","expected_version":0}
```

The API returns synthetic-only provenance, state, event sequence and hash-chain head; **not** raw card/IP data or automated fraud assertions.

## Security limits / nonclaims

- **Authentication:** HMAC-signed local **demo** bearer tokens with role, expiration, issued time, audience, issuer and random token ID. This is actual cryptographic signature verification, but it **does not establish a real employee identity**, support enterprise OIDC/SSO, MFA, key rotation, account revocation, hardware-backed keys or production authentication.
- **Audit:** SQLite triggers + keyed hash chain detect unauthorized database-only tampering *without possession of the audit key*. A privileged operator controlling the local service, audit secret, DB and backups can rewrite history. There is **no independent audit anchoring, retention, replicated audit service or compliance assurance**.
- **Replay:** idempotent cases/reviews and optimistic version checks are tested with synthetic fixtures, including real-service Kafka replay. These are **not** evidence of correctness under distributed concurrent reviewer traffic, multi-tenant isolation or production latency.
- **Decisions:** the only possible decisions are administrative *human review states*. No operational payment approval, denial, legal accusation or adverse action; SHAP attribution is explicitly non-causal.
- **Model:** simulated fraud labels, GBP-only model and synthetic test FPR 9.375% despite 5% validation FPR target; external ground truth, uncertainty, calibration/fairness and legal compliance are **not** established.
- **Legacy UI/API:** the existing frontend case page and `ml/serving/api.py` have **not** been wired to this signed local review API. This PR creates a secure-by-default local review endpoint and verifies the source-to-human-case sequence **in CI**; it does **not** claim an authenticated production dashboard.

## Next milestone

Productize a **local analyst-facing UI** that reads *only* this authenticated review API and renders verified signed SHAP bar plots and history, clearly labelled synthetic. Then add production-grade external OIDC/RBAC, reliable append-only audit anchoring, model monitoring, and real-world licensed dataset validation only after approvals.
