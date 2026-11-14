# CloudWatch Log Group com retenção definida (evita custos eternos de logs no CloudWatch)
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${var.project_name}-daily"
  retention_in_days = 14
}

# Função Serverless AWS Lambda
resource "aws_lambda_function" "cost_monitor_lambda" {
  function_name    = "${var.project_name}-daily"
  description      = "Coleta diária de custos AWS via Cost Explorer e publicação de relatório no S3"
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.12"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  filename         = "${path.module}/../lambda_package.zip"
  source_code_hash = filebase64sha256("${path.module}/../lambda_package.zip")

  environment {
    variables = {
      S3_BUCKET_NAME   = aws_s3_bucket.reports.id
      COST_PERIOD_DAYS = tostring(var.cost_period_days)
      COST_GRANULARITY = var.cost_granularity
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda_logs,
    aws_iam_role_policy.lambda_least_privilege,
  ]
}
