resource "aws_s3_bucket" "main" {
  bucket = "${local.name_prefix}-bucket"

  force_destroy = true
}

resource "aws_s3_bucket_versioning" "main" {
  bucket = aws_s3_bucket.main.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "main" {
  bucket = aws_s3_bucket.main.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "main" {
  bucket = aws_s3_bucket.main.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_object" "folders" {
  for_each = toset([
    "training/raw/",
    "training/processed/",
    "training/validation/",
    "inference/input/",
    "inference/output/",
    "models/candidates/",
    "models/champion/",
    "models/archived/",
    "logs/"
  ])

  bucket  = aws_s3_bucket.main.id
  key     = each.value
  content = ""
}
