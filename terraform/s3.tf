resource "random_id" "bucket_suffix" {
  byte_length = 4
}

locals {
  bucket_name = var.s3_bucket_name != null ? var.s3_bucket_name : "${var.project_name}-reports-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "reports" {
  bucket        = local.bucket_name
  force_destroy = false
}

resource "aws_s3_bucket_website_configuration" "reports_website" {
  bucket = aws_s3_bucket.reports.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_ownership_controls" "reports_ownership" {
  bucket = aws_s3_bucket.reports.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "reports_public_access" {
  bucket = aws_s3_bucket.reports.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "public_read_website" {
  depends_on = [aws_s3_bucket_public_access_block.reports_public_access]
  bucket     = aws_s3_bucket.reports.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.reports.arn}/*"
      }
    ]
  })
}
