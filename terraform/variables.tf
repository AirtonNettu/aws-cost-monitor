variable "aws_region" {
  description = "Região da AWS para provisionamento dos recursos."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nome base do projeto para prefixo de recursos."
  type        = string
  default     = "aws-cost-monitor"
}

variable "environment" {
  description = "Ambiente de execução (ex: prod, dev, staging)."
  type        = string
  default     = "prod"
}

variable "s3_bucket_name" {
  description = "Nome customizado para o bucket S3 de relatórios (se nulo, será gerado com sufixo aleatório)."
  type        = string
  default     = null
}

variable "cost_period_days" {
  description = "Período em dias para a coleta de custos da AWS (default: 30)."
  type        = number
  default     = 30
}

variable "cost_granularity" {
  description = "Granularidade da consulta ao Cost Explorer (DAILY ou MONTHLY)."
  type        = string
  default     = "DAILY"
  validation {
    condition     = contains(["DAILY", "MONTHLY"], var.cost_granularity)
    error_message = "A granularidade de custo deve ser 'DAILY' ou 'MONTHLY'."
  }
}

variable "cron_expression" {
  description = "Expressão cron do EventBridge para disparo automático diário (default: 11:00 UTC = 08:00 BRT)."
  type        = string
  default     = "cron(0 11 * * ? *)"
}

variable "lambda_timeout" {
  description = "Tempo limite de execução da Lambda em segundos (máximo recomendado para FinOps: 30s)."
  type        = number
  default     = 30
}

variable "lambda_memory_size" {
  description = "Quantidade de memória da Lambda em MB (128 MB mantém o custo estritamente no Free Tier)."
  type        = number
  default     = 128
}
