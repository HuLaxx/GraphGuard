# GraphGuard frontend — verified local review + illustrative GraphQL demo

The Next.js application has **two distinct paths**. The `/cases` signed local synthetic analyst desk uses the actual hash-pinned Python review API and displays real native SHAP values. The separate `/demo` GraphQL experience can use illustrative/fallback data and is **not** proof of a live bank transaction system.

## Reproduce the signed synthetic review desk

From the **repository root** with Python 3.11 and Node.js 20:

```bash
python -m pip install -r requirements-review-ci.txt
npm --prefix frontend ci
python -m ml.review.run_local_demo
```

Open `http://127.0.0.1:3000/cases`. The runner creates a deterministic synthetic ledger/model and a pre-opened real review case. It generates **separate private reviewer and audit keys**, plus short-lived analyst/admin tokens in `.local/graphguard-review/reviewer_tokens.json` (Git-ignored; mode 0600; never share). Paste the analyst token into the in-memory password field to inspect and escalate. Reconnect with the admin token to close an escalated case.

The signed review HTTP API is bound to `127.0.0.1:8765`. The Next.js same-origin proxy is deliberately restricted to `NODE_ENV=development` and an exact allowlist, so a Vercel production build **cannot proxy a remote signed-review service**. There is no fake case or risk-score fallback on `/cases`.

Use [the full local desk runbook](../docs/LOCAL_REVIEW_DASHBOARD.md) for security caveats, trusted SHA setup and test commands. Local quickstart directly seeds ledger fixtures; the full Kafka/Avro/Neo4j→model→SHAP→case path is verified separately in CI.

## Frontend checks

```bash
npm --prefix frontend run lint
npm --prefix frontend run type-check
npm --prefix frontend run test
npm --prefix frontend run build
```

The standalone graph, GraphQL, RAG and legacy dashboard components remain in this codebase. Do not interpret them as a verified full-stack production integration or as real fraud detection. Signed SHAP values are model attributions in log odds, **not proof of actual fraud or causality**.
