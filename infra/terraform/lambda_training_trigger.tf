data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "training_trigger_lambda_role" {
  name               = "${local.name_prefix}-training-trigger-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "training_trigger_lambda_policy" {
  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.training_trigger_lambda.arn}:*"
    ]
  }

  statement {
    sid    = "AllowStartStepFunctionsExecution"
    effect = "Allow"

    actions = [
      "states:StartExecution"
    ]

    resources = [
      aws_sfn_state_machine.ml_pipeline.arn
    ]
  }
}

resource "aws_iam_policy" "training_trigger_lambda_policy" {
  name        = "${local.name_prefix}-training-trigger-lambda-policy"
  description = "Allow Lambda to start Step Functions ML pipeline executions."
  policy      = data.aws_iam_policy_document.training_trigger_lambda_policy.json
}

resource "aws_iam_role_policy_attachment" "training_trigger_lambda_policy_attachment" {
  role       = aws_iam_role.training_trigger_lambda_role.name
  policy_arn = aws_iam_policy.training_trigger_lambda_policy.arn
}

resource "aws_cloudwatch_log_group" "training_trigger_lambda" {
  name              = "/aws/lambda/${local.name_prefix}-training-trigger"
  retention_in_days = 7

  tags = {
    Name = "${local.name_prefix}-training-trigger-logs"
  }
}

data "archive_file" "training_trigger_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../../api/lambdas/training_trigger_api"
  output_path = "${path.module}/build/training_trigger_lambda.zip"
}

resource "aws_lambda_function" "training_trigger" {
  function_name = "${local.name_prefix}-training-trigger"
  description   = "Starts Step Functions ML pipeline when a training CSV is uploaded to S3."

  role    = aws_iam_role.training_trigger_lambda_role.arn
  handler = "handler.lambda_handler"
  runtime = "python3.12"
  timeout = 60

  filename         = data.archive_file.training_trigger_lambda.output_path
  source_code_hash = data.archive_file.training_trigger_lambda.output_base64sha256

  environment {
    variables = {
      STATE_MACHINE_ARN = aws_sfn_state_machine.ml_pipeline.arn
      S3_BUCKET_NAME    = aws_s3_bucket.main.bucket
      OUTPUT_URI        = "s3://${aws_s3_bucket.main.bucket}/models/candidates"
      CHAMPION_URI      = "s3://${aws_s3_bucket.main.bucket}/models/champion"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.training_trigger_lambda,
    aws_iam_role_policy_attachment.training_trigger_lambda_policy_attachment
  ]

  tags = {
    Name = "${local.name_prefix}-training-trigger"
  }
}

resource "aws_lambda_permission" "allow_s3_invoke_training_trigger" {
  statement_id  = "AllowS3InvokeTrainingTrigger"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.training_trigger.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.main.arn
}

resource "aws_s3_bucket_notification" "training_raw_trigger" {
  bucket = aws_s3_bucket.main.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.training_trigger.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "training/raw/"
    filter_suffix       = ".csv"
  }

  depends_on = [
    aws_lambda_permission.allow_s3_invoke_training_trigger
  ]
}
