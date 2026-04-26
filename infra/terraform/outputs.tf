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

output "model_registry_table_name" {
  description = "DynamoDB table name for the model registry."
  value       = aws_dynamodb_table.model_registry.name
}

output "model_registry_table_arn" {
  description = "DynamoDB table ARN for the model registry."
  value       = aws_dynamodb_table.model_registry.arn
}

output "ecr_repository_name" {
  description = "ECR repository name for the ML pipeline image."
  value       = aws_ecr_repository.ml_pipeline.name
}

output "ecr_repository_url" {
  description = "ECR repository URL for the ML pipeline image."
  value       = aws_ecr_repository.ml_pipeline.repository_url
}

output "ecr_repository_arn" {
  description = "ECR repository ARN for the ML pipeline image."
  value       = aws_ecr_repository.ml_pipeline.arn
}

output "vpc_id" {
  description = "VPC ID used by ECS Fargate tasks."
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs used by ECS Fargate tasks."
  value       = aws_subnet.public[*].id
}

output "ecs_tasks_security_group_id" {
  description = "Security group ID for ECS Fargate tasks."
  value       = aws_security_group.ecs_tasks.id
}
