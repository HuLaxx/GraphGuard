<div align="center">

<img src="docs/assets/evidence-graph-hero.svg" width="100%" alt="Original animated forensic casefile visual: a sample transaction connected to accounts, devices and merchants" />

### GRAPHGUARD / THE EVIDENCE GRAPH

**Fraud rarely leaves a single clue. The important part is what the clues connect.**

A graph-informed fraud investigation project exploring **event ingestion, relationship analysis, XGBoost scoring, explainability and case review**.

[**Inspect the demo**](https://graph-guard-frontend.vercel.app) · [**Follow the evidence**](#follow-the-evidence) · [**Evidence register**](#evidence-register) · [**Progress & release gates**](docs/PROGRESS_SCORECARD.md) · [**Run locally**](#open-the-case-locally)

<sub>The animated hero uses fictional entities and relationships. It is not live transaction data, a measured risk score or an actual investigation.</sub>

</div>

---

## Current engineering evidence — 22 November 2026

**Release readiness: [70/100 verified](docs/PROGRESS_SCORECARD.md), draft and synthetic-only; not a production fraud model.** This is an evidence-weighted engineering score, not a real-world classification score or percentage of a hosted deployment.

- [PR #14](https://github.com/HuLaxx/GraphGuard/pull/14): **10/10 green full CI jobs** on [exact commit `868b7584`](https://github.com/HuLaxx/GraphGuard/actions/runs/44844565253), including real Kafka/Avro/Schema Registry/Neo4j, leakage-safe PIT features, a SHA-pinned tabular model, genuine native SHAP, signed local human case, **real Chromium analyst/admin review**, npm full-tree high/critical audit and security scan.
- [PR #15](https://github.com/HuLaxx/GraphGuard/pull/15) adds **one new same-event Kafka→Chromium runner** and a real signed local p50/p95 benchmark. **Pending GitHub Actions verification**: do not claim passed or increase the readiness percentage until there are green exact-head CI results.
- [Synthetic research model card](docs/MODEL_CARD.md): XGBoost test PR-AUC 0.7650, **test FPR 9.375%** despite a validation FPR target of 5%; no real-world fraud accuracy, fairness, or automated decision claims.
- [Run the signed local analyst desk](docs/LOCAL_REVIEW_DASHBOARD.md) · [Source-to-case architecture](docs/VERIFIED_ARCHITECTURE.md) · [Live evidence register](docs/EVIDENCE_REGISTER.md). The publicly hosted GraphQL demo is **illustrative** and is **not** the signed Python case service.

**Still required for genuine 100/100 release readiness:** independent licensed data with defensible cold-start labels, enterprise OIDC/MFA and audited retention, independently anchored case audit, tested production load/alerts/rollback, reviewed infrastructure cost and approved deployment/teardown, external security and model review, and explicit merge approvals. None are implied by local synthetic CI.
## Case opening / One event is not the whole story

Consider a **fictional example**: a purchase looks routine on its own, but the device appears on several accounts, which in turn connect to related merchants. Those relationships deserve inspection—not an automatic verdict.

> **Can we reveal the context behind a suspicious transaction, explain the model's reasoning and help an analyst decide what to examine next?**

GraphGuard's codebase explores that question. It separates **evidence**, **model output**, **explanation** and **reviewer action**. Some of the implementation is modular or local-first; not every service in the architectural vision is active in the hosted demo.

## Follow the evidence

<div align="center">
<img src="docs/assets/investigation-trail.svg" width="100%" alt="Five-step conceptual evidence trail: event intake, graph construction, risk scoring, explanations, human case review" />

<sub>Conceptual module map. This does not certify a complete live production pipeline.</sub>
</div>

<table>
<tr>
<td width="50%" valign="top">

**01 / What happened?**

The event producer provides the Kafka-facing intake path.

[Transaction producer](data-eng/producers/transaction_ingester.py) · [Event schema](data-eng/schemas/transaction_event.avsc)

</td>
<td width="50%" valign="top">

**02 / What's connected?**

The consumer and Neo4j tools reconstruct relationships that flat records can hide.

[Graph builder](data-eng/consumers/graph_builder.py) · [Graph algorithms](data-eng/neo4j/graph_algorithms.cypher)

</td>
</tr>
<tr>
<td width="50%" valign="top">

**03 / What is the estimated risk?**

A reproducible synthetic-only logistic/XGBoost baseline trains on past-only `pit-v1` features. The hash-pinned local scorer is tested; the legacy hosted API is a separate, unverified serving path.

[Reproducible baselines](ml/training/pit_baselines.py) · [Verified offline scoring](ml/serving/verified_pit_scorer.py)

</td>
<td width="50%" valign="top">

**04 / Why that output?**

SHAP tooling and explanatory charts make model contributions inspectable; an explanation is not causal proof.

[Verified native TreeSHAP](ml/explainability/verified_shap.py) · [Signed review attribution chart](frontend/src/components/review/verified-shap-chart.tsx)

</td>
</tr>
<tr>
<td colspan="2" valign="top">

**05 / What should the analyst review?**

The new signed **local** analyst case UI reads real synthetic case records, SHAP values and review history from the verified FastAPI review service. The separate GraphQL demo may still be illustrative.

[Signed case desk](frontend/src/app/cases/page.tsx) · [Review API](ml/review/app.py) · [Local quickstart](docs/LOCAL_REVIEW_DASHBOARD.md)

</td>
</tr>
</table>

## Verified local synthetic case desk (stacked review branch)

The updated [case desk](frontend/src/app/cases/page.tsx) does **not** ship with a mock fallback. It only renders the cases and signed native TreeSHAP values returned by the local review API, and reports when the API is unavailable or a token has expired. Analysts may escalate a synthetic case; only a signed demo admin may close one. Review history remains linked to source, feature, model and explanation hashes.

After installing Python and Node dependencies:

```bash
python -m pip install -r requirements-review-ci.txt
npm --prefix frontend ci
python -m ml.review.run_local_demo
```

Open `http://127.0.0.1:3000/cases` and use the private local reviewer token generated in `.local/graphguard-review/reviewer_tokens.json`. **Never publish or commit this file.** The quickstart directly seeds the local ledger to make the UI easy to reproduce; the full registered Avro → Kafka/Schema Registry → Neo4j → real model → SHAP → signed case journey is independently exercised in Docker-backed GitHub Actions integration tests.

This is a **synthetic-only review system**, not a deployed fraud classifier, a real customer case, enterprise SSO or a compliance-grade audit record. [Full reproducibility and security limitations](docs/LOCAL_REVIEW_DASHBOARD.md).

## Inside the investigation desk

<div align="center">
<img src="docs/assets/graphguard-demo.gif" width="86%" alt="Existing GraphGuard demo animation; an interface preview, not evidence of a connected live backend" />

<sub>Legacy illustrative demo capture, **not** a screenshot of the newer signed local analyst case desk. The separate GraphQL demo can show illustrative/fallback data.</sub>
</div>

Beyond a generic analytics dashboard, the project includes a [demo view](frontend/src/app/demo/page.tsx), [case investigation page](frontend/src/app/cases/page.tsx), [network graph](frontend/src/components/dashboard/network-graph.tsx), [SHAP component](frontend/src/components/dashboard/shap-chart.tsx) and [local-first RAG assistant](frontend/src/components/assistant/rag-assistant.tsx).

### Hosted demo ≠ full local stack

| Where | What's represented |
| :--- | :--- |
| **Hosted project website** | Lightweight frontend experience; mocked/fallback data is possible. Current live integration was **not** independently checked for this README refresh. |
| **Signed local analyst desk (`/cases`)** | Uses locally generated synthetic transactions, a real trained model, native SHAP values and short-lived signed demo reviewer identities. Runs **only in local development**; no publicly hosted case API. |
| **Local Docker services** | Compose files for PostgreSQL, Neo4j, Kafka, Flink and monitoring. Services require local resources and configuration. |
| **Python API and frontend** | Started separately; scoring, graph, model and RAG capabilities depend on credentials, services and available artifacts. |
| **Proposed hosted architecture** | Terraform and managed-service targets are plans/templates, not proof of completed production deployment. |

[Deployment reality check](docs/PRODUCTION_DEPLOYMENT.md) · [Implementation inventory](docs/PROJECT_CHECKLIST.md)

## Evidence register

**No claim without a trail back to code or an artifact.**

| Exhibit | Question | Evidence | Caveat |
| :--- | :--- | :--- | :--- |
| **E-01** | How do events enter the system? | [Producer](data-eng/producers/transaction_ingester.py) · [Consumer](data-eng/consumers/graph_builder.py) | Requires local services |
| **E-02** | How are patterns represented? | [Neo4j](data-eng/neo4j/) · [Flink](data-eng/flink/) · [Feature repo](data-eng/feast/feature_repo/) | Full pipeline not freshly verified |
| **E-03** | Where does scoring happen? | [Training](ml/training/train_xgboost_rigorous.py) · [API](ml/serving/api.py) | Model availability varies |
| **E-04** | Where are outputs explained? | [SHAP](ml/explainability/shap_analysis.py) · [UI](frontend/src/components/dashboard/shap-chart.tsx) | Not proof of causality |
| **E-05** | How does a case reach a reviewer? | [GraphQL](backend/graphql/resolvers.py) · [Case page](frontend/src/app/cases/page.tsx) | Case page includes mock data |
| **E-06** | How does repo-aware RAG work? | [Indexer](ml/serving/rag/indexer.py) · [RAG router](ml/serving/rag/router.py) · [Guide](docs/RAG.md) | Optional providers/settings |
| **E-07** | What testing exists? | [Python test log](docs/evidence/python-tests-20260124-210720.txt) · [API sample](docs/evidence/api-score-20260124-214043.txt) · [Audit](docs/FINAL_AUDIT.md) | Saved evidence, not live CI |

The saved test log reports **32 Python tests passing on January 24, 2026**; this is dated evidence rather than a current passing badge. The [source audit](docs/FINAL_AUDIT.md) explicitly records **GAT scoring as stubbed** and **Terraform as a template**.

## Open the case locally

The documented workflow uses **Docker Compose for supporting services**, with the Python API and Next.js interface started separately.

Prerequisites: Python 3.11+, a Node.js version compatible with Next.js 16, Docker/Compose for the backing stack, and enough system resources for the services selected.

~~~bash
git clone https://github.com/HuLaxx/GraphGuard.git
cd GraphGuard
cp .env.example .env
~~~

Configure local environment variables required by [Docker Compose](docker-compose.yml), including POSTGRES_PASSWORD, NEO4J_AUTH and GRAFANA_ADMIN_PASSWORD. Do not commit credentials.

~~~bash
# Optional backing services. May be resource-intensive.
docker compose up -d

# Python API from the repository root (another terminal).
python -m venv .venv
source .venv/bin/activate
pip install -e "./ml[dev]"
python -m uvicorn ml.serving.api:app --reload --port 8000

# Frontend from a separate terminal.
npm --prefix frontend install
npm --prefix frontend run dev
~~~

Windows venv activation: **.venv\Scripts\activate**. The API may need environment settings and keys for protected endpoints. Source-aligned commands above have **not** been re-tested end-to-end during this visual makeover.

| Local surface | URL |
| :--- | :--- |
| API reference | http://127.0.0.1:8000/docs |
| Health | http://127.0.0.1:8000/health |
| Frontend | http://localhost:3000 |

The optional [RAG assistant setup](docs/RAG.md) documents indexing, retrieval settings and providers separately.

### Scoring and investigation endpoints

| Route | What it exposes | Evidence |
| :--- | :--- | :--- |
| POST /score | Transaction scoring | [FastAPI](ml/serving/api.py) |
| GET /health | API health | [FastAPI](ml/serving/api.py) |
| GET /metrics | Prometheus metrics | [Monitoring](ml/monitoring/performance_monitoring.py) |
| POST /rag/ingest | Local RAG indexing | [Router](ml/serving/rag/router.py) |
| POST /rag/query | Ask over an index | [Router](ml/serving/rag/router.py) |

### Reproduce the checks

~~~bash
# After setting up Python dependencies
python -m pytest tests/unit/test_rag.py -v
python -m pytest tests/ -q

# In another terminal
npm --prefix frontend run test
~~~

These commands have **not** been executed during this README redesign. Historical logs and smoke results are stored in [docs/evidence](docs/evidence/).

## The unfinished case

Fraud investigation requires disciplined uncertainty: clear model provenance, measured errors, valid data, and a human review path.

- [x] Code paths for events, graph features, scoring, explanations and investigation interface.
- [x] Historical testing, API smoke logs and a source-level [audit](docs/FINAL_AUDIT.md).
- [x] Explicit separation of mocked UI cases, local services and proposed deployment.
- [ ] Replace/validate stubbed GAT scoring if that path is part of the intended application.
- [x] Verified the **local synthetic** registered Kafka→Neo4j→PIT→trained model/SHAP→signed reviewer case path, with repeatable CI [PR #13](https://github.com/HuLaxx/GraphGuard/pull/13). Same broker event in Chromium remains candidate in [PR #15](https://github.com/HuLaxx/GraphGuard/pull/15).
- [x] Re-ran full CI with **10/10 jobs green** and real Chromium/ingestion artifacts [PR #14](https://github.com/HuLaxx/GraphGuard/pull/14) [CI 44844565253](https://github.com/HuLaxx/GraphGuard/actions/runs/44844565253). Does not imply production readiness.
- [ ] Evaluate precision, recall, false-positive costs and bias on labeled data before citing performance.
- [ ] Verify the hosted demo's actual integration boundaries and document them.
- [ ] Review old example credentials and secrets before any external deployment.

[Detailed implementation inventory](docs/PROJECT_CHECKLIST.md) · [Creative makeover checklist](docs/CREATIVE_CHECKLIST.md)

---

<div align="center">

### THE EVIDENCE MATTERS MORE THAN THE ALERT.

A portfolio project by **Rahul Khanke / HuLaX**

[**Project website**](https://graph-guard-frontend.vercel.app) · [**Portfolio**](https://portfolio.hulax.uk/) · [**GitHub**](https://github.com/HuLaxx) · [**LinkedIn**](https://www.linkedin.com/in/rahul-khanke-853717218/)

<sub>Illustrative diagrams and sample data are not live risk judgments.</sub>

</div>
