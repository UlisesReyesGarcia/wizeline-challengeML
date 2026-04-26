resource "aws_cloudwatch_log_group" "prediction_api_lambda" {
  name              = "/aws/lambda/${local.name_prefix}-prediction-api"
  retention_in_days = 7

  tags = {
    Name = "${local.name_prefix}-prediction-api-logs"
  }
}

resource "aws_iam_role" "prediction_api_lambda_role" {
  name               = "${local.name_prefix}-prediction-api-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "prediction_api_lambda_policy" {
  statement {
    sid    = "AllowCloudWatchLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.prediction_api_lambda.arn}:*"
    ]
  }

  statement {
    sid    = "AllowReadPredictionInputsAndChampion"
    effect = "Allow"

    actions = [
      "s3:GetObject"
    ]

    resources = [
      "${aws_s3_bucket.main.arn}/inference/input/*",
      "${aws_s3_bucket.main.arn}/inference/output/*",
      "${aws_s3_bucket.main.arn}/models/champion/*"
    ]
  }

  statement {
    sid    = "AllowWritePredictionOutputs"
    effect = "Allow"

    actions = [
      "s3:PutObject"
    ]

    resources = [
      "${aws_s3_bucket.main.arn}/inference/output/*"
    ]
  }
}

resource "aws_iam_policy" "prediction_api_lambda_policy" {
  name        = "${local.name_prefix}-prediction-api-lambda-policy"
  description = "Allow prediction API Lambda to read inputs, read champion model and write outputs."
  policy      = data.aws_iam_policy_document.prediction_api_lambda_policy.json
}

resource "aws_iam_role_policy_attachment" "prediction_api_lambda_policy_attachment" {
  role       = aws_iam_role.prediction_api_lambda_role.name
  policy_arn = aws_iam_policy.prediction_api_lambda_policy.arn
}

resource "aws_lambda_function" "prediction_api" {
  function_name = "${local.name_prefix}-prediction-api"
  description   = "Runs batch predictions using the champion model stored in S3."

  package_type = "Image"
  image_uri    = "${aws_ecr_repository.prediction_api.repository_url}:latest"

  role        = aws_iam_role.prediction_api_lambda_role.arn
  timeout     = 300
  memory_size = 2048

  environment {
    variables = {
      S3_BUCKET_NAME        = aws_s3_bucket.main.bucket
      CHAMPION_MODEL_URI    = "s3://${aws_s3_bucket.main.bucket}/models/champion/model.pkl"
      PREDICTION_OUTPUT_URI = "s3://${aws_s3_bucket.main.bucket}/inference/output"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.prediction_api_lambda,
    aws_iam_role_policy_attachment.prediction_api_lambda_policy_attachment,
    aws_ecr_repository.prediction_api
  ]

  tags = {
    Name = "${local.name_prefix}-prediction-api"
  }
}
