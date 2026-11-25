# FleetFlow P3 — review-only, low-cost AWS analytics infrastructure

[Draft PR #13](https://github.com/HuLaxx/FleetFlow/pull/13) stacks on
[draft PR #12](https://github.com/HuLaxx/FleetFlow/pull/12). **Zero AWS
resources have been created**. Terraform configuration is not a deployment.

## Proposed optional topology

```text
Manually reviewed anonymised / synthetic batch Parquet
     |
     +--> S3 review lake: raw/ clean/ curated/ (SSE-S3, versioned, private)
     |       | raw expiry 7d, clean 30d, curated 90d by default
     |       v
     +--> Glue Catalog namespace ONLY (no crawler or actual table creation)
     |       v
     +--> Athena review workgroup (1 GiB max scan per query by default)
     |       +--> private SSE-S3 results bucket (7d expiry)
     +--> optional CloudWatch log namespace (7d retention)
     +--> optional $5 USD/month 80%-spend AWS Budgets email alert
```

**Not implemented by these Terraform files:** CDC, Lambda, EventBridge,
Glue table definitions, ingestion worker, KMS customer-managed keys, a
production server, authorization rules for private query results, monitoring
alarms, per-tenant security boundary, cloud benchmarking or S3 objects.
Catalog and workgroup creation alone do not constitute a functioning
end-to-end analytics warehouse. CloudWatch log group does not receive
telemetry automatically. The P2 Parquet replay is *local*, not S3 ingestion.

## Defaults and guardrails

| Control | Value / status |
| --- | --- |
| AWS account | Explicit twelve-digit account ID; provider restricts account |
| Deployment authorization | `owner_approved = false` by default; S3 lifecycle precondition blocks planning/applying until reviewed |
| State | No backend configured; do NOT deploy with unaudited local state; pre-create encrypted locked remote state |
| Lake privacy | S3 Block Public Access, BucketOwnerEnforced, SSE-S3 at rest, HTTPS-only bucket policy, no ACLs |
| Object retention | raw 7d, clean 30d, curated 90d; noncurrent versions expire after 7d |
| Query spend safeguard | Athena single-query scan cutoff 1 GiB, enforced by workgroup |
| Query results | Separate private SSE-S3 bucket; `results/` expires after 7 days |
| Diagnostics | Empty CloudWatch log group, 7-day retention; not connected to workers |
| Monthly budget alert | Optional and **disabled by default**; if enabled 80% of $5 USD monthly actual-spend alert |
| CI IAM/OIDC | Optional and disabled; only narrow readonly audit role with `sub` restricted to `HuLaxx/FleetFlow:refs/heads/main` and `aud` `sts.amazonaws.com`; requires existing account OIDC provider |
| Destructive cleanup | `force_destroy=false` for both buckets; deliberate object/version removal needed |
| Cost | **No hard cap**; bill accrues for storage, Athena queries, requests, logs, budgets beyond free allowance and data transfer |

AWS Budgets alerts are delayed notifications and **not a kill switch**.
Athena's scan ceiling limits one query's scan size, **not total monthly
queries**. Retention does not replace privacy, deletion request or consent
policy. SSE-S3 is server-managed encryption, not KMS key isolation.
No claim of an infrastructure security audit.

## Reproduce without AWS credentials or expenses

```bash
cd infra/terraform/aws-lakehouse
terraform fmt -check -diff -recursive
terraform init -backend=false -input=false
terraform validate
```

These commands validate **module syntax and provider schema**, not account
permissions, IAM policy implementation, cost limits, deployability,
state-lock correctness or running services. The dedicated
`.github/workflows/p3-terraform-review.yml` invokes ONLY those commands
without GitHub `id-token` permission, any AWS credentials, `plan`,
`apply` or `destroy`. The validation workflow must be green before
reviewers may treat the module as syntactically plausible.

## Owner-only future deployment preparation (NOT executed)

1. Choose account, region, a **unique** S3 prefix and AWS credentials
   with only the provision permissions approved for this module.
2. Review cost estimation in the chosen region using the official
   [S3](https://aws.amazon.com/s3/pricing/),
   [Athena](https://aws.amazon.com/athena/pricing/) and
   [AWS Budgets](https://aws.amazon.com/aws-cost-management/aws-budgets/pricing/)
   pricing pages; this PR does not quote a bill. Prepare an
   **independently reviewed monthly budget and billing alerts**.
3. Have the account owner review privacy/retention, data access,
   bucket naming, OIDC IAM provider and remote-state encryption/locking.
   Approve `owner_approved=true` and if needed
   `enable_budget_alert=true` and private alert email through an
   untracked Terraform variables file.
4. Configure a **separate remote Terraform backend with an encrypted
   locked state and a narrowly scoped role**. This module does not create
   that backend to avoid self-management/secret leakage.
5. Only after explicit manual sign-off, generate a real account-scoped
   Terraform **plan** and review diffs. Any potential *apply*, test
   data upload, and *destroy* are separate explicit approval gates.
   Do not issue them from CI.
6. A rollback/teardown plan must account for versioned S3 objects and
   delete markers; `force_destroy=false` intentionally blocks a
   blind bucket deletion. Even a successful destroy may not immediately
   stop all charges (log/query billing delays).

## Independent verifiability

- Terraform module: `infra/terraform/aws-lakehouse/`
- Offline CI: `.github/workflows/p3-terraform-review.yml`
- Sources for Terraform resource schema:
  [Athena workgroup](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/athena_workgroup),
  [Glue database](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/glue_catalog_database),
  [S3 bucket](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket).
- Actual account plan, cost forecast, remote-state test and cloud deployment:
  **not run**. If CI validation fails, use the exact log and fix the
  Terraform configuration before reporting any success.
