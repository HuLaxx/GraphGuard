# FleetFlow / Spark + Databricks + dbt + optional Azure

**Status: REVIEW BRANCH / NOT DEPLOYED.** All GPS data below must be synthetic. This
addition does not merge the upstream draft stack or change the hosted demo.

## Architectural boundary

```text
Synthetic authenticated GPS -> existing Kafka/PostGIS -> accepted JSONL snapshot
       -> existing replay validation/quarantine -> immutable clean Parquet
               |                                   |
               +-> existing Postgres hourly load -> dbt GPS fact + observed dimensions
               |
               +-> real PySpark aggregate -> optional Databricks Delta managed table

Azure review-only Terraform -> private ADLS Gen2 storage foundation
                             -> optional gated Container App for an externally
                                supplied backend image, PostGIS and broker
```

**Important:** The Databricks Free Edition workspace is independent of the
user's Azure subscription. Provisioning an Azure Storage account does not
connect it to Databricks or imply that the notebook has accessed Azure data.
The hosted FleetFlow site remains a fixture-backed portfolio frontend unless
a real backend deployment is independently verified.

## 1. Build a source snapshot (local)

From the repository root with dependencies installed:

```bash
python -m pip install -e './backend[lake]'
PYTHONPATH=backend python -m src.lakehouse.replay \
  --input /absolute/path/to/synthetic-gps.jsonl --output /tmp/fleetflow-lake
```

The command reports the content-addressed directory
`/tmp/fleetflow-lake/runs/<run_key>/`. Inspect `manifest.json` and validate
each listed checksum before importing data anywhere else. Accepted GPS Parquet
lives under `clean/event_date=*/telemetry.parquet` (or `clean/empty.parquet`).
**Never** upload real vehicle/person locations to a free demonstration account.

## 2. Rebuild the batch aggregation in actual local Spark

```bash
python -m pip install 'pyspark==3.5.6' 'pytest==8.3.5'
PYTHONPATH=data-engineering/spark SPARK_LOCAL_HOSTNAME=localhost \
  python -m pytest -q data-engineering/spark/test_fleetflow_batch.py
```

The Spark module reads accepted replay Parquet, groups by observed vehicle and
UTC hour, counts accepted/late records, computes mean *observed* speed and
selects a deterministic most-recent coordinate. It rejects duplicate IDs and
out-of-contract records. It does **not** stream Kafka, provision a Spark
cluster, infer drive distance, or forecast ETA. The existing Python replay
remains the raw-event contract and quarantine authority.

## 3. Run in Databricks Free Edition

1. Create a Free Edition workspace using the official Azure Databricks signup
   route. Do not start a paid Azure Databricks workspace just for this exercise.
2. Import the repository as a Git folder. Open
   `data-engineering/spark/fleetflow_databricks.py` as a notebook with the
   sibling `fleetflow_batch.py` present.
3. Upload the **entire original run directory** (manifest, raw, clean, quarantine)
   into a Unity Catalog Volume you control (for example
   `/Volumes/<catalog>/<schema>/<volume>/<run_key>/`).
4. Fill widget parameters: `manifest_path` pointing at the uploaded JSON and,
   only when publishing, `output_table` in `catalog.schema.table` form. The
   notebook discovers exact clean files from the manifest, verifies the SHA-256
   for every artifact, and reconciles Spark event/late counts before writing.
5. Run in **preview** mode first. Review displayed rows and original run
   counts. Set `publish=yes` only for a new, dedicated Delta table. The
   notebook refuses to overwrite a pre-existing table.
6. Record a screenshot of the successful Spark execution, SQL count query,
   Delta table path, workspace/runtime version, cost/usage quota and execution
   date in the evidence register. Do not claim Databricks until this executes.

The manifest checks establish byte integrity against the supplied manifest,
not the authenticity of whoever authored that manifest. Keep the run synthetic.

The notebook does not create an Azure storage credential, production table or
external integration. Free Edition quotas and feature availability can change.

## 4. dbt star model on the existing PostgreSQL warehouse

The star now contains:

| Model | Grain / join key | Measure or intent |
| --- | --- | --- |
| `fct_gps_hourly` | one replay + vehicle + UTC hour, `gps_hour_key` | observed event count, late count, measured speed |
| `dim_observed_vehicle` | one replay + vehicle, `vehicle_run_key` | first/last observed hours, not fleet inventory |
| `dim_utc_date` | one observed UTC calendar day, `utc_date_key` | calendar attributes only |

Both dimension keys are linked to the fact through schema relationship tests.
A singular SQL test rejects impossible late counts and out-of-hour latest
positions. The existing actual local PostGIS/dbt CI must pass on this branch
before marking warehouse coverage verified. This does not fabricate order
delivery KPIs or driver availability.

## 5. Terraform: Azure review infrastructure, not an executed deployment

`infra/azure/` provisions a resource group and private, HTTPS-only hierarchical
storage foundation. A Container App, its environment and Log Analytics are
**disabled by default** via `deploy_api=false`. The opt-in API depends on
an actual published backend container image plus reachable PostGIS and Kafka,
none of which are automatically created by this module.

Static review only (no Azure credentials or billable resources needed):

```bash
terraform -chdir=infra/azure fmt -check -recursive
terraform -chdir=infra/azure init -backend=false
terraform -chdir=infra/azure validate
```

For a later *approved* cloud deployment, first establish budget/credit,
subscription quota, suitable region, secured remote state, least-privilege
identity/RBAC, non-public network connectivity, real database+broker,
container registry access, image provenance, health/recovery checks and a
teardown plan. Then authenticate with `az login`, choose the subscription,
provide a **unique** storage name and inspect `terraform plan`. Never run
`terraform apply` by default. Resources and observability can incur charges
even where a service has a monthly free allowance. Strong secrets passed to
Terraform can be stored in state; keep it encrypted and access-controlled.

With public ingress disabled, the optional API Container App has no public
endpoint. Enabling public ingress without completing the authz, TLS/domain,
rate-limit, monitoring and integration review is not a production release.

## 6. Optional Snowflake experiment

Do not claim Snowflake until a separate free-trial workspace actually executes
a translated version of the observed GPS star model and its relationship /
freshness checks. These models currently use PostgreSQL-specific SQL casts,
`TO_CHAR` and intervals; they are **not** portable to Snowflake merely by
changing a dbt profile. A Snowflake trial is optional, not a dependency of the
FleetFlow core golden path.

## Release gate

P0/P1 upstream issues, 24/7 operational reliability, real Azure / Databricks
execution, cloud cost measurement, security and approved draft-stack merge
remain separate work. Add dated CI run URLs, exact commit and workspace proof
to `docs/EVIDENCE_REGISTER.md` once verified. Until then, label every new
integration as **code committed / CI pending / cloud not executed**.
