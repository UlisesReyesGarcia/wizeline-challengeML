resource "aws_sfn_state_machine" "ml_pipeline" {
  name     = "${local.name_prefix}-ml-pipeline-state-machine"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = jsonencode({
    Comment = "Orchestrates the wizeline-challengeML training pipeline on ECS Fargate"
    StartAt = "RunMLPipelineTask"

    States = {
      RunMLPipelineTask = {
        Type     = "Task"
        Resource = "arn:aws:states:::ecs:runTask.sync"

        Parameters = {
          LaunchType     = "FARGATE"
          Cluster        = aws_ecs_cluster.ml_pipeline.arn
          TaskDefinition = aws_ecs_task_definition.ml_pipeline.arn

          NetworkConfiguration = {
            AwsvpcConfiguration = {
              Subnets        = aws_subnet.public[*].id
              SecurityGroups = [aws_security_group.ecs_tasks.id]
              AssignPublicIp = "ENABLED"
            }
          }

          Overrides = {
            ContainerOverrides = [
              {
                Name = "ml-pipeline"

                Environment = [
                  {
                    Name  = "S3_BUCKET_NAME"
                    Value = aws_s3_bucket.main.bucket
                  },
                  {
                    Name  = "MODEL_REGISTRY_TABLE"
                    Value = aws_dynamodb_table.model_registry.name
                  },
                  {
                    Name  = "AWS_REGION"
                    Value = var.aws_region
                  },
                  {
                    Name  = "PROJECT_NAME"
                    Value = var.project_name
                  },
                  {
                    Name  = "ENVIRONMENT"
                    Value = var.environment
                  },
                  {
                    Name      = "TRAINING_DATA_URI"
                    "Value.$" = "$.training_data_uri"
                  },
                  {
                    Name      = "OUTPUT_URI"
                    "Value.$" = "$.output_uri"
                  },
                  {
                    Name      = "CHAMPION_URI"
                    "Value.$" = "$.champion_uri"
                  }
                ]
              }
            ]
          }
        }

        End = true
      }
    }
  })

  tags = {
    Name = "${local.name_prefix}-ml-pipeline-state-machine"
  }
}
