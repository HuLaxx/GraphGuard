variable "aws_region" {
  description = "AWS region for the opt-in analytics sandbox"
  type        = string
  default     = "eu-west-2"
}

variable "environment" {
  description = "Only isolated nonproduction environments are allowed"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "test"], var.environment)
    error_message = "This reviewed module cannot create production resources."
  }
}

variable "lake_bucket_name" {
  description = "Human-approved globally unique private S3 bucket name"
  type        = string
  validation {
    condition     = length(var.lake_bucket_name) >= 3 && length(var.lake_bucket_name) <= 63
    error_message = "Provide an S3 bucket name of 3-63 characters."
  }
}

variable "github_oidc_provider_arn" {
  description = "Pre-existing reviewed IAM GitHub OIDC provider ARN; not provisioned here"
  type        = string
  validation {
    condition     = can(regex("^arn:aws:iam::[0-9]{12}:oidc-provider/token[.]actions[.]githubusercontent[.]com$", var.github_oidc_provider_arn))
    error_message = "Use the reviewed token.actions.githubusercontent.com OIDC provider ARN."
  }
}
