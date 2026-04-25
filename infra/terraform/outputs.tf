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
