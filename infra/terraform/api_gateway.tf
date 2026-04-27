resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-http-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_credentials = false
    allow_headers = [
      "authorization",
      "content-type"
    ]
    allow_methods = [
      "GET",
      "POST",
      "OPTIONS"
    ]
    allow_origins = [
      "*"
    ]
    max_age = 300
  }

  tags = {
    Name = "${local.name_prefix}-http-api"
  }
}

resource "aws_apigatewayv2_authorizer" "cognito_jwt" {
  name             = "${local.name_prefix}-cognito-jwt-authorizer"
  api_id           = aws_apigatewayv2_api.main.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]

  jwt_configuration {
    audience = [
      aws_cognito_user_pool_client.frontend.id
    ]

    issuer = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.main.id}"
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  tags = {
    Name = "${local.name_prefix}-http-api-default-stage"
  }
}

resource "aws_apigatewayv2_integration" "upload_api" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.upload_api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "prediction_api" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.prediction_api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "model_registry_api" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.model_registry_api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "training_trigger_api" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.training_trigger.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "upload_url" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /upload-url"
  target             = "integrations/${aws_apigatewayv2_integration.upload_api.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito_jwt.id
}

resource "aws_apigatewayv2_route" "predictions" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /predictions"
  target             = "integrations/${aws_apigatewayv2_integration.prediction_api.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito_jwt.id
}

resource "aws_apigatewayv2_route" "model_registry_champion" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "GET /model-registry/champion"
  target             = "integrations/${aws_apigatewayv2_integration.model_registry_api.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito_jwt.id
}

resource "aws_apigatewayv2_route" "retrain" {
  api_id             = aws_apigatewayv2_api.main.id
  route_key          = "POST /retrain"
  target             = "integrations/${aws_apigatewayv2_integration.training_trigger_api.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito_jwt.id
}

resource "aws_lambda_permission" "allow_apigateway_upload_api" {
  statement_id  = "AllowApiGatewayInvokeUploadApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.upload_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "allow_apigateway_prediction_api" {
  statement_id  = "AllowApiGatewayInvokePredictionApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.prediction_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "allow_apigateway_model_registry_api" {
  statement_id  = "AllowApiGatewayInvokeModelRegistryApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.model_registry_api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "allow_apigateway_training_trigger_api" {
  statement_id  = "AllowApiGatewayInvokeTrainingTriggerApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.training_trigger.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}
