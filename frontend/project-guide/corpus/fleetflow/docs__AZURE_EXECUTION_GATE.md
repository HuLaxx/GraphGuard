# Azure release execution gate — FleetFlow

**State on 22 November 2026: NONE DEPLOYED OR PAID FOR BY THIS PR.**

The infrastructure under `infra/azure` and the manual workflow
`.github/workflows/p3-azure-review-deploy.yml` are a **reviewable deployment
route** for the *actual* FleetFlow API. This is not proof of a live Azure
deployment. The hosted frontend continues to be separate. GitHub-hosted
runners cannot serve as private network peers to a database or event broker.

## Decisions before applying anything

1. **Budget and subscription**: identify Azure subscription, region, quotas
   and a monthly spending cap with alert notifications. Confirm cost of
   Storage, Log Analytics, Container Apps, private endpoints, PostGIS and
   Kafka. Container Apps may include a monthly free grant but the entire
   architecture is **not free** and quotas may change. No work is allowed
   to claim all components fit a zero-cost tier.
2. **Sensitive data**: synthetic GPS only for portfolio testing. Determine
   retention, privacy, access controls and region before real telemetry.
3. **External data plane**: prepare an accessible, secured PostgreSQL
   database with **PostGIS** and reviewed schema migrations, plus a real
   TLS-enabled Kafka-compatible broker. Neither is created by this minimal
   Terraform module. Private ingress defaults to false and the app will
   not be reachable from the public internet.
4. **Actual API image**: build, vulnerability-scan and publish the
   `backend/Dockerfile` image to a registry the Azure Container App can
   read, pinned to an immutable digest. If using a private registry, add
   reviewed managed-identity pull access; the example does not implement
   registry authentication.
5. **Environment security**: configure GitHub environment
   `azure-review` with a required human approval rule. Add branch
   restrictions and audit trail. Do not assume the workflow automatically
   configures those rules.
6. **Identity**: create an Azure workload-identity federation to GitHub
   Actions, restricted to this repository's `azure-review` environment,
   with least-privilege resource-group access, not tenant-wide admin.
7. **Terraform state**: bootstrap a separate Azure Blob state storage account
   and container with Azure AD RBAC, encryption, access restrictions,
   logging, retention and state locking. The application lake storage
   account is different from the *preexisting* state store. No local
   runner Terraform state for an actual deployment.
8. **Runtime readiness**: add a real public health/reachability route
   through an approved ingress path or internal probe, verify DNS/TLS,
   CORS, auth, restart/replay, backup/restore, alerts, costs and teardown.

## Required GitHub configuration

*Repository-level variables*, available to the preflight guard:

- `AZURE_TFSTATE_RG`: existing state storage resource group
- `AZURE_TFSTATE_ACCOUNT`: existing state account name
- `AZURE_TFSTATE_CONTAINER`: existing Blob state container
- `AZURE_FLEETFLOW_STORAGE_NAME`: **globally unique** application lake account
- `AZURE_FLEETFLOW_API_IMAGE`: immutable reviewed image reference (when enabling API)
- `AZURE_FLEETFLOW_KAFKA_SERVERS`: TLS/private broker address (when enabling API)
- `AZURE_FLEETFLOW_BUDGET_REVIEWED`: set `true` **only after** real budget review

*Environment secrets*, under the protected `azure-review` environment:

- `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`
- `FLEETFLOW_DATABASE_URL` (only for actual API deployment)
- `FLEETFLOW_JWT_SECRET_KEY` (only for actual API deployment, at least 32 chars)

The GitHub OIDC identity requires appropriate Azure control-plane RBAC and
Blob Data Contributor access to the **separate** state container. Terraform
sensitive values can appear in remote state; protect that state and rotate
credentials. Do not enter secrets in issues, PRs or `.tfvars` files.

## Manual flow

The workflow dispatch action becomes discoverable when the workflow exists
on the repository default branch after reviewed merge. Select a reviewed
ref. Run `operation=plan` first and inspect changes with the team. It uses
OIDC and the remote state backend. **No `apply` happens on plan.**

Only after budget, security and environment approval, run
`operation=apply` and enter the exact acknowledgement
`I_ACCEPT_AZURE_CHARGES`. That job executes Terraform apply using the
approved plan and existing state store. The workflow deliberately does not
create the external PostGIS/Kafka services; `deploy_api` defaults false.
If enabled, deploy and verify backend ingress and event replay separately.

## Evidence required to mark Azure complete

Capture without sensitive values: subscription alias, repo commit,
Terraform state revision, plan/apply run URLs, Azure resource IDs, digest of
container actually running, health and real contract verification from an
authorised network, log/metric alerts, measured cost and teardown/recreate
proof. **Azure code validated** and **Azure app deployed** are different
completion states. Never publish private endpoints, secrets or customer GPS.

## Teardown

Only destroy resources in the dedicated Terraform state using a reviewed
`terraform plan -destroy`, within an approved change and retention
window. Ensure data/backups are preserved before deleting state or
resources. Never destroy another project's group by name alone.
