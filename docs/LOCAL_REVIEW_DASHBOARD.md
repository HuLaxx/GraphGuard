# GraphGuard — signed local analyst dashboard

**Scope:** a reviewable, authenticated **local synthetic-only** interface backed by the actual `ml/review/app.py` endpoints. The hosted GraphQL demo is separate and may still contain example/fallback views. This UI **never** inserts fake cases, scores, SHAP values or review history.

## One-command local demo

Prerequisites: Python 3.11, Node.js 20, npm, and a clean checkout of the **stacked PR #10 branch**. Nothing requires AWS, paid APIs, actual customers or Docker for this quick UI fixture.

```bash
python -m pip install -r requirements-review-ci.txt
npm --prefix frontend ci
python -m ml.review.run_local_demo
```

Open **http://127.0.0.1:3000/cases**. The runner generates `.local/graphguard-review/` on the first execution, including:

- `models/manifest.json` and deterministic 240-row synthetic baseline model artifacts, with independently pinned source/model hashes;
- `synthetic_ledger.sqlite3`, containing three accepted synthetic ledger events with immutable `pit-v1` snapshots; one case is opened with the real native SHAP explanation, and another transaction can be opened manually;
- `private_config.json` and `reviewer_tokens.json` with file permissions **0600**. They are private credentials in a Git-ignored `.local/` directory. Do not commit, screenshot, publish, paste into issues or send them to others.

Read the current **analyst** token from the private `reviewer_tokens.json` locally, paste it into the password field on the case page, then select the pre-opened case. You can inspect the signed audit events and actual SHAP log-odds chart, escalate the case, then disconnect and reconnect using the separate **admin** token to close the escalated case. Admin-only closure is enforced by the Python server (not only hidden in the browser).

The second accepted synthetic transaction ID is `synthetic-ui-review-002`; enter it in the case-creation form to open another case. The browser creates unique idempotency keys, sends versioned review actions, and refreshes records from the signed local API. No payment is approved or rejected.

Tokens expire after 600 seconds; stop/restart the runner to mint fresh local tokens. The reviewer and audit signing secrets remain unchanged inside the private configuration for stable local audit verification. Use a **different workspace** for a clean fixture instead of overwriting the ledger.

The runner binds the Python review service to **127.0.0.1:8765** and Next development to **127.0.0.1:3000**. Ctrl-C terminates both. It does not expose an HTTPS endpoint or launch any cloud service.

### What the dashboard does and does not prove

| Verified component | Scope |
|---|---|
| Token verification | Separate, short-lived local HMAC-signed analyst/admin demo tokens; not real enterprise identity |
| Case list and detail | Actual signed API responses from the local SQLite source/model evidence |
| Native SHAP chart | Actual 12 ordered model features, signed log-odds contributions, reconstruction and non-causality notice |
| Human review | State transitions, admin-only closure, optimistic concurrency, replay-safe HMAC-linked local audit |
| Quick-start data | **Directly seeded SQLite first-observed ledger**, not a fresh live Kafka event |
| Full ingestion golden path | Separate Docker-backed **real Kafka + Avro Schema Registry + Neo4j → model → SHAP → case** in GitHub Actions integration tests |
| Hosted frontend | **NOT** connected to the local signed API; Next.js route bridge returns 404 outside development mode |

### The local signed API boundary

The browser sends its short-lived token in `Authorization: Bearer …` only. The same-origin Next.js route `frontend/src/app/review-local/[[...path]]/route.ts` is available **only under `NODE_ENV=development`**. It whitelists exactly the local `/session`, `/cases`, case-detail, verified-explanation and review-action paths; rejects arbitrary URLs; forwards only to fixed `127.0.0.1:8765`; bounds POST payload and response size; never caches answers; and does not save credentials in cookies or browser localStorage.

Signed API responses are rechecked server-side before case data and numeric SHAP are returned. The frontend also checks the model, source, snapshot, explanation hashes and score consistency before rendering a selected case. Auth errors, unavailable local services and stale optimistic versions have explicit messages and no mock fallback.

### Commands for independently verifying this PR

```bash
python -m pytest tests/unit/test_synthetic_review.py -v
python -m pytest tests/unit/test_pit_baselines.py tests/unit/test_verified_pit_scorer.py tests/unit/test_verified_shap.py tests/unit/test_synthetic_review.py -v
npm --prefix frontend run lint
npm --prefix frontend run type-check
npm --prefix frontend run test
npm --prefix frontend run build
```

CI also starts disposable Kafka, Confluent Schema Registry and Neo4j and executes `tests/integration/test_avro_registry.py`. Verify current-head green CI; local quick-start directly seeds SQLite and **does not** claim broker integration from the browser alone.

## Production release gates still open

- No external OIDC/SSO/MFA or real identity proof. The HMAC demo tokens and local SQLite audit are **not** compliant enterprise authentication/independent audit anchoring.
- No deployed public GraphGuard review UI or cloud API. No Terraform apply, AWS account usage or billable resources. A Vercel-hosted version of this page cannot connect to the local signing service.
- This experiment uses **synthetic labels** and GBP-only model fixtures. Prior synthetic XGBoost holdout false-positive rate was **9.375%**, above the validation-selected 5% target. This is not real-world fraud model performance or an automated decision rule.
- Published SHAP values are correlations with model output, **not causal explanations**, individual accusations or fairness certification.
- No signed browser-based e2e automation under Playwright or performance measurement yet; the React/Vitest component tests, backend TestClient tests and full Kafka/Docker integration are distinct, inspectable checks.
- No production auth rate-limiting, external log anchoring, full dependency lockfile audit, public data validation, model registry/rollback, drift alerts or tested AWS deployment. Those remain explicit P0–P4 gates.

**Source and evidence:** [PR #10](https://github.com/HuLaxx/GraphGuard/pull/10) and [GraphGuard release checklist](ENGINEERING_RELEASE_CHECKLIST.md). Do not call this a fully production-ready 10/10 system solely because the synthetic golden path runs.
