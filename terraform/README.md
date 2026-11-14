# 🚀 Infraestrutura como Código (Terraform) — AWS Cost Monitor

Módulo Terraform oficial para provisionamento 100% automatizado da arquitetura Serverless do **AWS Cost Monitor** no regime **AWS Free Tier (Custo Zero)**.

---

## 🏛️ Recursos Provisionados

| Recurso | Tipo / Serviço | Função |
|---|---|---|
| `aws_s3_bucket.reports` | Amazon S3 | Hospedagem estática do dashboard HTML (`index.html`). |
| `aws_s3_bucket_website_configuration` | S3 Website Hosting | Configuração de ponto de extremidade web público. |
| `aws_iam_role.lambda_role` | AWS IAM | Role de execução com princípio de menor privilégio. |
| `aws_iam_role_policy.lambda_least_privilege` | IAM Policy Inline | Acesso estrito a `ce:GetCostAndUsage` e `s3:PutObject`. |
| `aws_lambda_function.cost_monitor_lambda` | AWS Lambda | Runtime Python 3.12 (128 MB, timeout 30s). |
| `aws_cloudwatch_log_group.lambda_logs` | CloudWatch Logs | Retenção controlada de logs (14 dias). |
| `aws_cloudwatch_event_rule.daily_trigger` | Amazon EventBridge | Agendamento diário (`cron(0 11 * * ? *)` = 08:00 BRT). |

---

## 📋 Pré-requisitos

1. **Terraform** `>= 1.5.0` instalado.
2. **AWS CLI** configurado com credenciais válidas (`aws configure`).
3. Pacote `lambda_package.zip` gerado na raiz do repositório.

---

## ⚡ Como Fazer o Deploy em 3 Passos

### 1. Gerar o pacote de código da Lambda
Na raiz do repositório:
```bash
python scripts/build_lambda_package.py
```

### 2. Inicializar o Terraform
Entre no diretório `terraform/`:
```bash
cd terraform
terraform init
```

### 3. Planejar e Aplicar
```bash
# Opcional: crie seu terraform.tfvars com base no example
cp terraform.tfvars.example terraform.tfvars

# Visualizar o plano de execução
terraform plan

# Aplicar o provisionamento na nuvem
terraform apply -auto-approve
```

---

## 🌐 Acessando seu Dashboard

Ao final do `terraform apply`, o Terraform exibirá os `Outputs`:
```text
Outputs:

eventbridge_schedule = "cron(0 11 * * ? *)"
lambda_function_name = "aws-cost-monitor-daily"
s3_bucket_name       = "aws-cost-monitor-reports-a1b2c3d4"
s3_website_endpoint  = "http://aws-cost-monitor-reports-a1b2c3d4.s3-website-us-east-1.amazonaws.com"
```

Basta abrir o link do `s3_website_endpoint` no navegador! 🚀

---

## 🧹 Destruição dos Recursos

Para remover todos os recursos criados da sua conta AWS:
```bash
terraform destroy -auto-approve
```
*(Nota: garanta que o bucket S3 esteja vazio antes de executar o destroy, ou adicione `force_destroy = true` no `s3.tf` durante testes).*
