# FleetFlow at a glance

## What FleetFlow is

FleetFlow is Rahul Khanke's logistics dispatch and fleet data-engineering project. It explores vehicle routing, event-driven logistics and operational visibility: from a depot's incoming orders to a route proposal a dispatcher can inspect, and from driver GPS events to a live map and an analytics warehouse. Live demo: https://fleet-flow-rho.vercel.app. Source: https://github.com/HuLaxx/FleetFlow.

## Tech stack

- Interface: Next.js 16, React 19, TypeScript, Tailwind CSS 4, tRPC, MapLibre and deck.gl maps.
- API and route planning: Python, FastAPI, SQLAlchemy and Google OR-Tools for vehicle routing with capacity and time-window constraints.
- Events and telemetry: Kafka (Redpanda in CI), a transactional outbox and inbox, a GPS consumer, WebSockets, PostgreSQL with PostGIS, TimescaleDB and Redis.
- Lakehouse: bronze CSV, a data-contract quality gate, a PySpark silver job (idempotent, date-partitioned Parquet) and a dbt star schema that runs on DuckDB and is Snowflake-compatible; orchestrated by an Airflow DAG and deployable to Databricks on Azure with Terraform (ADLS Gen2, Databricks, Key Vault).
- Infrastructure and quality: Docker Compose, Kubernetes (kind) manifests, Terraform for Azure and a review-only AWS module, GitHub Actions CI, Playwright browser tests, Prometheus/Grafana-style pipeline observability.
- Machine learning: chronological demand-forecasting baselines and route-planning baseline evaluations on synthetic data.

## How route planning works

A dispatcher picks a depot and date, FleetFlow loads vehicles and pending orders, OR-Tools models vehicle capacity, depot location, route duration and service windows, and the solver returns candidate routes. The optimize endpoint is a read-only preview; a separate plan endpoint persists a planned route, and approval is a separate, authorised dispatcher decision. A dedicated CI benchmark compares OR-Tools with a capacity- and window-aware greedy baseline on synthetic 8-stop, 12-stop and infeasible cases.

## How GPS reaches the map

An authenticated driver posts GPS events to the FastAPI backend, which writes them through a PostgreSQL outbox to Kafka/Redpanda; a GPS consumer stores positions in PostGIS and pushes them to the browser over WebSockets. This journey passed a non-mocked Chromium CI run with synthetic input on disposable PostGIS and Redpanda services.

## What is verified and what is not

Verified in CI with synthetic data: the authenticated GPS to Kafka to PostGIS to WebSocket browser journey; immutable Parquet replay with clean/curated reconciliation; dbt builds with passing data tests; Airflow DAG import and dependency validation; the OR-Tools benchmark; the lakehouse pipeline end to end. Not claimed: a production deployment, real fleet or customer data, live hosted backend behind the public demo, a real Apache Flink job (the event processor is a simplified Python module), or provisioned AWS resources (the AWS Terraform is review-only). Several milestones live in stacked draft pull requests rather than merged code; the evidence register records each one.
