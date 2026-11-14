# Regra de Agendamento Diário no Amazon EventBridge
resource "aws_cloudwatch_event_rule" "daily_trigger" {
  name                = "${var.project_name}-daily-trigger"
  description         = "Dispara a função AWS Lambda diariamente para atualizar a fatura no S3"
  schedule_expression = var.cron_expression
}

# Alvo da regra: Função AWS Lambda
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_trigger.name
  target_id = "CostMonitorLambdaTarget"
  arn       = aws_lambda_function.cost_monitor_lambda.arn
}

# Permissão para o EventBridge invocar a Lambda
resource "aws_lambda_permission" "allow_eventbridge_invoke" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_monitor_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_trigger.arn
}
