# Fase 3: Multi-Conta & AWS Organizations (Padrão Enterprise)

Em empresas maduras, ninguém usa uma única conta da AWS. O padrão corporativo é ter dezenas de contas separadas gerenciadas pelo **AWS Organizations**:
- `Conta 1: Produção (Prod)`
- `Conta 2: Homologação (Staging)`
- `Conta 3: Desenvolvimento (Dev)`
- `Conta 4: Dados / Analytics`
- `Conta 5: Auditoria / FinOps Central`

Nesta fase, você ensina o `aws-cost-monitor` a monitorar **múltiplas contas da AWS ao mesmo tempo** a partir de um único ponto central.

---

## 1. Arquitetura de Delegação (Cross-Account IAM Roles)

```
┌─────────────────────────────────────────────────────────────────┐
│ Conta Central FinOps (Onde roda a sua Lambda / Dashboard)       │
└────────────────┬────────────────────────────────────────────────┘
                 │ AssumeRole (STS) com credencial temporária
        ┌────────┴────────────────────────┐
        ▼                                 ▼
┌───────────────────────┐       ┌───────────────────────┐
│ Conta Filha: Prod     │       │ Conta Filha: Dev      │
│ Role: FinOpsAuditRole │       │ Role: FinOpsAuditRole │
└───────────────────────┘       └───────────────────────┘
```

A conta central não precisa das chaves mestras de ninguém. Cada conta filha cria uma IAM Role chamada `FinOpsAuditRole` permitindo que a conta central assuma a role via `sts:AssumeRole`.

---

## 2. Como Funciona a Troca de Contexto com Boto3

```python
import boto3


def get_cost_client_for_account(account_id: str, role_name: str = "FinOpsAuditRole"):
    """Assume uma role em uma conta externa e retorna um cliente Cost Explorer autorizado."""
    sts_client = boto3.client("sts")

    role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"
    response = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName="FinOpsMonitorSession"
    )

    credentials = response["Credentials"]

    # Cria cliente do Cost Explorer usando as credenciais temporárias da conta filha
    return boto3.client(
        "ce",
        region_name="us-east-1",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
```

---

## 3. Valor de Mercado dessa Funcionalidade
Um profissional que sabe implementar monitoramento Multi-Conta com `AssumeRole` e AWS Organizations passa na frente de 98% dos candidatos em entrevistas para vagas de **Cloud Architect / FinOps Lead**, pois resolve o maior problema de gestão de nuvem de médias e grandes empresas.
