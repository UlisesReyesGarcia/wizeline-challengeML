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

output "ecs_task_execution_role_arn" {
  description = "IAM role ARN used by ECS to execute Fargate tasks."
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "ecs_task_role_arn" {
  description = "IAM role ARN used by the ML pipeline container."
  value       = aws_iam_role.ecs_task_role.arn
}

output "ecs_cluster_name" {
  description = "ECS cluster name for ML pipeline tasks."
  value       = aws_ecs_cluster.ml_pipeline.name
}

output "ecs_cluster_arn" {
  description = "ECS cluster ARN for ML pipeline tasks."
  value       = aws_ecs_cluster.ml_pipeline.arn
}

output "ecs_task_definition_arn" {
  description = "ECS task definition ARN for the ML pipeline."
  value       = aws_ecs_task_definition.ml_pipeline.arn
}

output "ml_pipeline_log_group_name" {
  description = "CloudWatch log group name for ML pipeline ECS tasks."
  value       = aws_cloudwatch_log_group.ml_pipeline.name
}

output "step_functions_role_arn" {
  description = "IAM role ARN used by Step Functions to orchestrate ECS tasks."
  value       = aws_iam_role.step_functions_role.arn
}

output "step_functions_state_machine_name" {
  description = "Step Functions state machine name for the ML pipeline."
  value       = aws_sfn_state_machine.ml_pipeline.name
}

output "step_functions_state_machine_arn" {
  description = "Step Functions state machine ARN for the ML pipeline."
  value       = aws_sfn_state_machine.ml_pipeline.arn
}

output "training_trigger_lambda_name" {
  description = "Lambda function name for S3 training batch trigger."
  value       = aws_lambda_function.training_trigger.function_name
}

output "training_trigger_lambda_arn" {
  description = "Lambda function ARN for S3 training batch trigger."
  value       = aws_lambda_function.training_trigger.arn
}

output "upload_api_lambda_name" {
  description = "Lambda function name for generating presigned upload URLs."
  value       = aws_lambda_function.upload_api.function_name
}

output "upload_api_lambda_arn" {
  description = "Lambda function ARN for generating presigned upload URLs."
  value       = aws_lambda_function.upload_api.arn
}

output "prediction_api_ecr_repository_name" {
  description = "ECR repository name for the prediction API Lambda image."
  value       = aws_ecr_repository.prediction_api.name
}

output "prediction_api_ecr_repository_url" {
  description = "ECR repository URL for the prediction API Lambda image."
  value       = aws_ecr_repository.prediction_api.repository_url
}

output "prediction_api_ecr_repository_arn" {
  description = "ECR repository ARN for the prediction API Lambda image."
  value       = aws_ecr_repository.prediction_api.arn
}

output "prediction_api_lambda_name" {
  description = "Lambda function name for batch predictions."
  value       = aws_lambda_function.prediction_api.function_name
}

output "prediction_api_lambda_arn" {
  description = "Lambda function ARN for batch predictions."
  value       = aws_lambda_function.prediction_api.arn
}

output "model_registry_api_lambda_name" {
  description = "Lambda function name for model registry API."
  value       = aws_lambda_function.model_registry_api.function_name
}

output "model_registry_api_lambda_arn" {
  description = "Lambda function ARN for model registry API."
  value       = aws_lambda_function.model_registry_api.arn
}

output "cognito_user_pool_id" {
  description = "Cognito User Pool ID."
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_arn" {
  description = "Cognito User Pool ARN."
  value       = aws_cognito_user_pool.main.arn
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool App Client ID for frontend authentication."
  value       = aws_cognito_user_pool_client.frontend.id
}

output "cognito_issuer_url" {
  description = "Cognito issuer URL used by API Gateway JWT authorizer."
  value       = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
}

output "api_gateway_id" {
  description = "HTTP API Gateway ID."
  value       = aws_apigatewayv2_api.main.id
}

output "api_gateway_endpoint" {
  description = "HTTP API Gateway endpoint."
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "api_gateway_authorizer_id" {
  description = "Cognito JWT authorizer ID for HTTP API Gateway."
  value       = aws_apigatewayv2_authorizer.cognito_jwt.id
}

output "frontend_bucket_name" {
  description = "S3 bucket name for frontend hosting."
  value       = aws_s3_bucket.frontend.bucket
}

output "frontend_cloudfront_distribution_id" {
  description = "CloudFront distribution ID for frontend hosting."
  value       = aws_cloudfront_distribution.frontend.id
}

output "frontend_cloudfront_domain_name" {
  description = "CloudFront domain name for frontend hosting."
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "frontend_url" {
  description = "Frontend URL served by CloudFront."
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}
