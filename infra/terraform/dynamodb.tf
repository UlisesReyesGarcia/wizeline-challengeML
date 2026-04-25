resource "aws_dynamodb_table" "model_registry" {
  name         = "${local.name_prefix}-model-registry"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "model_id"

  attribute {
    name = "model_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }
}
