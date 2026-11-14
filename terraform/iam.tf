# Role IAM para execução da função AWS Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Permissão básica para envio de logs estruturados ao CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Política customizada de Menor Privilégio (Least Privilege): Cost Explorer + S3 PutObject
resource "aws_iam_role_policy" "lambda_least_privilege" {
  name = "${var.project_name}-least-privilege-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "CostExplorerReadOnly"
        Effect   = "Allow"
        Action   = [
          "ce:GetCostAndUsage"
        ]
        Resource = "*"
      },
      {
        Sid      = "S3PutReportOnly"
        Effect   = "Allow"
        Action   = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.reports.arn}/*"
      }
    ]
  })
}
