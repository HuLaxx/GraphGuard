# Sentinance at a glance

## What Sentinance is

Sentinance is Rahul Khanke's real-time crypto and market intelligence project. It explores how raw exchange data becomes structured signals, model outputs and AI-assisted analysis, while keeping observed prices, predictions and generated explanations clearly separate. Demo: https://sentinance.vercel.app. Source: https://github.com/HuLaxx/Sentinance.

## Tech stack

- Frontend: Next.js 16, React 18, TypeScript, Tailwind CSS, Vitest and Playwright tests.
- APIs and streaming: Python, FastAPI, WebSockets with Redis Pub/Sub, server-sent events, JWT authentication.
- Data: versioned Kafka events, a duplicate-safe PostgreSQL price-event ledger, TimescaleDB for price history, immutable checksum-verified Parquet snapshots, dbt models with data-quality tests on DuckDB.
- Machine learning: technical indicators, a chronological ridge autoregression forecast compared with last-price and moving-average baselines, and an optional PyTorch LSTM experiment.
- AI and retrieval: a LangGraph research agent that only explains a move when it can cite evidence, Gemini and Groq integrations with fallbacks, and Qdrant retrieval evaluated in CI.
- Platform: Docker Compose, Kubernetes and monitoring configurations, Prometheus metrics, GitHub Actions CI, review-only Terraform for an AWS S3/Glue/Athena analytics sandbox.

## How data flows

A source adapter validates aggregate-trade payloads with source-owned IDs, publishes them to Kafka, and a consumer persists them to a PostgreSQL ledger with a unique source/symbol/ID constraint so replays are idempotent. A local source checkpoint and receipt reconciliation detect events that were acknowledged by Kafka but never reached the database and replay them. The ledger exports raw, validated and curated Parquet snapshots that dbt builds into marts; a forecast report is produced from the curated data and cited by the LangGraph evidence path, then shown in the Next.js evidence page.

## What is verified and what is not

Verified with synthetic data in CI: the fixture source to real Kafka to PostgreSQL to checked Parquet to historical forecast to citation to browser journey; 463 API tests on the reviewed revision; repeated 9-step dbt builds; a Chromium test that rejects a deliberately corrupted model report; offline Terraform validation; a Qdrant retrieval evaluation (dense recall@5 0.979 on a small synthetic corpus). Not claimed: live production price streaming, deployed AWS services, profitable or live forecast accuracy, live LSTM accuracy, full LLM evaluation or real user traffic. The deterministic LangGraph evidence path makes no LLM requests.
