output "s3_bucket_name" {
  description = "Nome do bucket S3 onde os relatórios HTML são publicados."
  value       = aws_s3_bucket.reports.id
}

output "s3_website_endpoint" {
  description = "URL pública de acesso ao dashboard no Amazon S3 Website Hosting."
  value       = "http://${aws_s3_bucket_website_configuration.reports_website.website_endpoint}"
}

output "lambda_function_name" {
  description = "Nome da função AWS Lambda provisionada."
  value       = aws_lambda_function.cost_monitor_lambda.function_name
}

output "lambda_function_arn" {
  description = "ARN da função AWS Lambda."
  value       = aws_lambda_function.cost_monitor_lambda.arn
}

output "iam_role_arn" {
  description = "ARN da Role IAM de execução com princípio de menor privilégio."
  value       = aws_iam_role.lambda_role.arn
}

output "eventbridge_schedule" {
  description = "Expressão de agendamento cron configurada no EventBridge."
  value       = aws_cloudwatch_event_rule.daily_trigger.schedule_expression
}
