# P3: Actual local Chromium analyst audit acceptance

The [real Chromium CI](../.github/workflows/ci.yml) now runs Next.js 16 **in local development only** and real loopback FastAPI + frozen verified synthetic model / native SHAP / SQLite audit. The browser:
1. Checks prominent synthetic-only labels and fails a deliberately invalid reviewer token.
2. Logs in with a private, short-lived analyst token. Browser token is held in React memory and submitted to the allowlisted same-origin Next bridge (disabled for production builds).
3. Opens the preseeded accepted synthetic transaction in the actual case UI, confirms real 12-feature SHAP and source/model/audit visuals.
4. Escalates through the browser, and independently verifies durable case version 1 and changed audit hash through the signed FastAPI API.
5. Disconnects, logs in as a distinct admin, closes the case through the browser, and independently verifies version 2, role sequence and unchanged hash-pinned model evidence.
6. Asserts that browser HTML and storage state contain no reviewer token; captures a synthetic-only final screenshot and sanitized lineage report with no secrets.

Run: install `requirements-review-ci.txt` plus `playwright==1.57.0`, `python -m playwright install chromium`, `npm --prefix frontend ci`, then `python -m ml.review.run_local_demo --workspace .local/chromium-check --browser-smoke --evidence-dir .local/browser-proof` from the repository root. Local signing tokens are generated per run, permissions remain restricted and are never uploaded. The golden browser path is **seeded from the local transaction ledger**, unlike the separate real Kafka/Neo4j→model→human case [P3 integration](P3_REAL_BROKER_TO_CASE.md) which starts at the broker. The two tests are intentionally not misrepresented as one uninterrupted broker-to-Chromium flow. No production backend, real customers, live bank accounts, graph GNN, cloud IAM, licensed fraud outcomes or AWS spending are involved. Case closure is only a human review state.
