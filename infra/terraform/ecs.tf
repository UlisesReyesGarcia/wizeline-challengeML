resource "aws_ecs_cluster" "ml_pipeline" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = {
    Name = "${local.name_prefix}-cluster"
  }
}

resource "aws_cloudwatch_log_group" "ml_pipeline" {
  name              = "/ecs/${local.name_prefix}-ml-pipeline"
  retention_in_days = 7

  tags = {
    Name = "${local.name_prefix}-ml-pipeline-logs"
  }
}

resource "aws_ecs_task_definition" "ml_pipeline" {
  family                   = "${local.name_prefix}-ml-pipeline-task"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "2048"
  memory                   = "4096"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "ml-pipeline"
      image     = "${aws_ecr_repository.ml_pipeline.repository_url}:latest"
      essential = true

      command = [
        "python",
        "ml_pipeline/src/main.py"
      ]

      environment = [
        {
          name  = "PROJECT_NAME"
          value = var.project_name
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "S3_BUCKET_NAME"
          value = aws_s3_bucket.main.bucket
        },
        {
          name  = "MODEL_REGISTRY_TABLE"
          value = aws_dynamodb_table.model_registry.name
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"

        options = {
          awslogs-group         = aws_cloudwatch_log_group.ml_pipeline.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = {
    Name = "${local.name_prefix}-ml-pipeline-task"
  }
}
