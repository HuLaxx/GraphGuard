# Sentinance — interview-ready claims (source-backed)

**Status:** Reviewable local **synthetic-data** AI Systems / Time-Series Data Engineering project. See [release evidence](RELEASE_CANDIDATE_2026_11_20.md) and [GitHub draft PR #35](https://github.com/HuLaxx/Sentinance/pull/35). Do not repeat the historical aspirational technology inventory as delivered production experience. The old inventory overclaimed senior-level competence, K8s production, MLflow, SHAP/LIME, Feature Store, and sliding-window rate limiting without matching whole-system deployment tests.

## One-line recruiter tagline

Built a traceable crypto-market investigation prototype using versioned Kafka events, a PostgreSQL ledger, immutable Parquet/dbt analytics, leakage-aware forecasting and a constrained LangGraph evidence trail — verified end-to-end with synthetic data in CI.

## LinkedIn Featured description (draft; publish only after final checks)

Sentinance is my AI-systems and time-series data engineering project. I wanted to explore a practical question: can a market-intelligence product show exactly where its facts come from? I built a synthetic-source replay through Kafka and PostgreSQL, exported checksum-verified Parquet snapshots, and ran dbt models with data-quality tests. A chronological forecasting benchmark compares a simple statistical model against last-price and moving-average baselines. A constrained LangGraph path reads a pinned evaluation report, recomputes metrics, and produces a traceable citation without inventing live prices. GitHub CI runs the full fixture journey in Chromium, including a deliberately corrupted report that the UI rejects. The demo and repository distinguish mock data, experimental models, local verification and unprovisioned cloud architecture. This is a reproducible engineering case study, not a live trading service.

## Case study

Exchange events carry identifiers and timestamps, but dashboards can easily flatten observed prices, derived indicators, forecasts and generated explanations into equally authoritative-looking values. I designed Sentinance to preserve those distinctions. The core source adapter validates aggregate-trade payloads and source-owned IDs. Kafka provides acknowledged event transport while a PostgreSQL ledger enforces duplicate-safe persistence. I added resumable local checkpoints and explicit receipt reconciliation because a broker ACK is not proof of database receipt. The ledger exports immutable raw, validated and curated Parquet snapshots with checksums. The data-model workflow loads an independently pinned snapshot into DuckDB and runs actual dbt mart builds twice to catch duplicates and stale transformations.

For forecasting, a chronological split fits ridge autoregression on log returns using only training data; validation selects regularization, and the held-out period is evaluated against last-close and moving-average baselines. The report records exact predictions, timestamps, model settings, dataset provenance and limitations. A deterministic LangGraph workflow reads a digest-pinned report, recomputes statistics and returns an explicit citation and tool-step trace; it does not call a real LLM or make investment recommendations. A read-only API and Next.js evidence page display the results. GitHub CI uses real disposable Kafka/PostgreSQL services and a Chromium test that corrupts the model artifact to prove the failure state.

The most important trade-off is deliberately leaving the public deployment, provider licensing and paid cloud services unverified. I chose a defensible synthetic golden path over invented live metrics.

## Interview story

**Challenge:** Kafka ACK does not imply a row is safely in PostgreSQL. **Decision:** maintain a local source cursor after ACK, detect unreceived IDs in a bounded range by checking the durable source ledger, explicitly replay missing source IDs and rely on a unique source/symbol/ID constraint for idempotency. **Failure test:** force a missing record; replay through Kafka; confirm the PostgreSQL row appears once and the browser does not label fixture data live. **Limitation:** local source checkpoint is not distributed exactly-once processing, and real exchange retention/licensing and cross-region recovery remain unproven.

## Appropriate and inappropriate claims

**Appropriate:** exact checked synthetic CI path; actual migrated Postgres and Kafka test services; Parquet/dbt validation; digest-pinned statistical forecasts and limited LangGraph evidence; AWS infrastructure *defined and offline-validated*.

**Inappropriate:** deployed AWS services; production real-time price streaming from Binance; profitable forecasts; live LSTM accuracy, full LLM/RAG evaluation, enterprise-grade ready status, saved production cost or real user traffic. Web deployment != verified draft backend deployment.

**Evidence:** [API CI](https://github.com/HuLaxx/Sentinance/actions/runs/44816859822), [dbt](https://github.com/HuLaxx/Sentinance/actions/runs/44816859900), [browser CI artifact](https://github.com/HuLaxx/Sentinance/actions/runs/44816859968), [offline Terraform](https://github.com/HuLaxx/Sentinance/actions/runs/44816859844). These links verify the earlier `fe44c78` branch revision, not later unverified additions.
