resource "aws_cloudwatch_log_group" "model_registry_api_lambda" {
  name              = "/aws/lambda/${local.name_prefix}-model-registry-api"
  retention_in_days = 7

  tags = {
    Name = "${local.name_prefix}-model-registry-api-logs"
  }
}

resource "aws_iam_role" "model_registry_api_lambda_role" {
  name               = "${local.name_prefix}-model-registry-api-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "model_registry_api_lambda_policy" {
  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.model_registry_api_lambda.arn}:*"
    ]
  }

  statement {
    sid    = "AllowReadChampionArtifacts"
    effect = "Allow"

    actions = [
      "s3:GetObject"
    ]

    resources = [
      "${aws_s3_bucket.main.arn}/models/champion/*"
    ]
  }
}

resource "aws_iam_policy" "model_registry_api_lambda_policy" {
  name        = "${local.name_prefix}-model-registry-api-lambda-policy"
  description = "Allow model registry API Lambda to read champion model metadata from S3."
  policy      = data.aws_iam_policy_document.model_registry_api_lambda_policy.json
}

resource "aws_iam_role_policy_attachment" "model_registry_api_lambda_policy_attachment" {
  role       = aws_iam_role.model_registry_api_lambda_role.name
  policy_arn = aws_iam_policy.model_registry_api_lambda_policy.arn
}

data "archive_file" "model_registry_api_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../../api/lambdas/model_registry_api"
  output_path = "${path.module}/build/model_registry_api_lambda.zip"
}

resource "aws_lambda_function" "model_registry_api" {
  function_name = "${local.name_prefix}-model-registry-api"
  description   = "Returns current champion model metadata and metrics."

  role    = aws_iam_role.model_registry_api_lambda_role.arn
  handler = "handler.lambda_handler"
  runtime = "python3.12"
  timeout = 30

  filename         = data.archive_file.model_registry_api_lambda.output_path
  source_code_hash = data.archive_file.model_registry_api_lambda.output_base64sha256

  environment {
    variables = {
      S3_BUCKET_NAME  = aws_s3_bucket.main.bucket
      CHAMPION_PREFIX = "models/champion"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.model_registry_api_lambda,
    aws_iam_role_policy_attachment.model_registry_api_lambda_policy_attachment
  ]

  tags = {
    Name = "${local.name_prefix}-model-registry-api"
  }
}
