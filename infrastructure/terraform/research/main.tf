# Review-only dev/test analytics scaffolding. No ingestion compute, API host,
# Glue ETL jobs, public endpoints or live fleet feed are created here.

data "aws_partition" "current" {}
data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "lake" {
  bucket        = var.lake_bucket_name
  force_destroy = false
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "lake" {
  bucket = aws_s3_bucket.lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_policy" "lake_tls_only" {
  bucket = aws_s3_bucket.lake.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyTransportWithoutTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [aws_s3_bucket.lake.arn, format("%s/*", aws_s3_bucket.lake.arn)]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      }
    ]
  })
  depends_on = [aws_s3_bucket_public_access_block.lake]
}

resource "aws_glue_catalog_database" "analytics" {
  name        = "graphguard_analytics_${var.environment}"
  description = "Metadata catalog for explicitly imported, original synthetic fraud research data"
}

resource "aws_athena_workgroup" "analytics" {
  name  = "graphguard_analytics_${var.environment}"
  state = "ENABLED"
  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = 1073741824 # 1 GiB/query, NOT a monthly cap.
    result_configuration {
      output_location = format("s3://%s/athena-results/", aws_s3_bucket.lake.id)
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}

# This role is for reviewing/small data movement only, NOT Terraform apply.
# GitHub environment "analytics-review" must have required reviewers.
resource "aws_iam_role" "github_analytics" {
  name = "graphguard-analytics-review-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRoleWithWebIdentity"
        Effect    = "Allow"
        Principal = { Federated = var.github_oidc_provider_arn }
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
            "token.actions.githubusercontent.com:sub" = "repo:HuLaxx/GraphGuard:environment:analytics-review"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "github_analytics" {
  name = "graphguard-analytics-prefixes-${var.environment}"
  role = aws_iam_role.github_analytics.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListOnlyTheSandboxBucket"
        Effect   = "Allow"
        Action   = ["s3:ListBucket"]
        Resource = [aws_s3_bucket.lake.arn]
        Condition = {
          StringLike = {
            "s3:prefix" = ["synthetic-datasets/*", "research-results/*", "model-artifacts/*", "athena-results/*"]
          }
        }
      },
      {
        Sid    = "ReadWriteOnlyAnalyticsPrefixes"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject"]
        Resource = [
          format("%s/synthetic-datasets/*", aws_s3_bucket.lake.arn),
          format("%s/research-results/*", aws_s3_bucket.lake.arn),
          format("%s/athena-results/*", aws_s3_bucket.lake.arn)
        ]
      },
      {
        Sid    = "ReadModelArtifactsOnly"
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = [format("%s/model-artifacts/*", aws_s3_bucket.lake.arn)]
      },
      {
        Sid      = "QueryOnlyNamedAthenaWorkgroup"
        Effect   = "Allow"
        Action   = ["athena:StartQueryExecution", "athena:GetQueryExecution", "athena:GetQueryResults"]
        Resource = [aws_athena_workgroup.analytics.arn]
      },
      {
        Sid    = "ReadOnlyCatalogMetadata"
        Effect = "Allow"
        Action = ["glue:GetDatabase", "glue:GetTable", "glue:GetTables"]
        Resource = [
          format("arn:%s:glue:%s:%s:catalog", data.aws_partition.current.partition, var.aws_region, data.aws_caller_identity.current.account_id),
          aws_glue_catalog_database.analytics.arn,
          format("arn:%s:glue:%s:%s:table/%s/*", data.aws_partition.current.partition, var.aws_region, data.aws_caller_identity.current.account_id, aws_glue_catalog_database.analytics.name)
        ]
      }
    ]
  })
}
