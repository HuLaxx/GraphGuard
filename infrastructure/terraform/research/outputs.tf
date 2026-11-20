output "private_lake_bucket_name" {
  value       = aws_s3_bucket.lake.id
  description = "Private, versioned and SSE-S3 encrypted analytics bucket"
}

output "athena_workgroup" {
  value       = aws_athena_workgroup.analytics.name
  description = "Bounded Athena query workgroup; per-query cutoff only"
}

output "glue_database" {
  value       = aws_glue_catalog_database.analytics.name
  description = "Metadata-only catalog; no ETL jobs created"
}

output "github_analytics_role_arn" {
  value       = aws_iam_role.github_analytics.arn
  description = "Limited OIDC reviewer role, not a Terraform deployment role"
}
