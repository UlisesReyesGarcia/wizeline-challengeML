resource "aws_cloudwatch_log_group" "upload_api_lambda" {
  name              = "/aws/lambda/${local.name_prefix}-upload-api"
  retention_in_days = 7

  tags = {
    Name = "${local.name_prefix}-upload-api-logs"
  }
}

resource "aws_iam_role" "upload_api_lambda_role" {
  name               = "${local.name_prefix}-upload-api-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "upload_api_lambda_policy" {
  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.upload_api_lambda.arn}:*"
    ]
  }

  statement {
    sid    = "AllowGeneratePresignedUploadUrls"
    effect = "Allow"

    actions = [
      "s3:PutObject"
    ]

    resources = [
      "${aws_s3_bucket.main.arn}/inference/input/*",
      "${aws_s3_bucket.main.arn}/training/raw/*"
    ]
  }
}

resource "aws_iam_policy" "upload_api_lambda_policy" {
  name        = "${local.name_prefix}-upload-api-lambda-policy"
  description = "Allow upload API Lambda to generate presigned S3 upload URLs."
  policy      = data.aws_iam_policy_document.upload_api_lambda_policy.json
}

resource "aws_iam_role_policy_attachment" "upload_api_lambda_policy_attachment" {
  role       = aws_iam_role.upload_api_lambda_role.name
  policy_arn = aws_iam_policy.upload_api_lambda_policy.arn
}

data "archive_file" "upload_api_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../../api/lambdas/upload_api"
  output_path = "${path.module}/build/upload_api_lambda.zip"
}

resource "aws_lambda_function" "upload_api" {
  function_name = "${local.name_prefix}-upload-api"
  description   = "Generates presigned URLs for CSV uploads to S3."

  role    = aws_iam_role.upload_api_lambda_role.arn
  handler = "handler.lambda_handler"
  runtime = "python3.12"
  timeout = 30

  filename         = data.archive_file.upload_api_lambda.output_path
  source_code_hash = data.archive_file.upload_api_lambda.output_base64sha256

  environment {
    variables = {
      S3_BUCKET_NAME = aws_s3_bucket.main.bucket
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.upload_api_lambda,
    aws_iam_role_policy_attachment.upload_api_lambda_policy_attachment
  ]

  tags = {
    Name = "${local.name_prefix}-upload-api"
  }
}
