output "project_name" {
  description = "Project name."
  value       = var.project_name
}

output "environment" {
  description = "Deployment environment."
  value       = var.environment
}

output "aws_region" {
  description = "AWS region."
  value       = var.aws_region
}

output "name_prefix" {
  description = "Common resource name prefix."
  value       = local.name_prefix
}

output "s3_bucket_name" {
  description = "Main S3 bucket name."
  value       = aws_s3_bucket.main.bucket
}

output "s3_bucket_arn" {
  description = "Main S3 bucket ARN."
  value       = aws_s3_bucket.main.arn
}
