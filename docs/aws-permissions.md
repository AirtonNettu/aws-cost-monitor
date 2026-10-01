# Integração e permissões AWS — AWS Cost Monitor V1

> Derivado do código real. Todos os identificadores aqui são fictícios.

## Serviços AWS utilizados

- **AWS Cost Explorer** (`ce`): usado no fluxo principal, em `src/aws/cost_explorer.py`.
- **AWS STS** (`sts`): usado apenas no script de verificação `src/test_aws.py`, fora do fluxo de `main`.

## APIs chamadas

| API | Onde | Finalidade |
|---|---|---|
| `ce:GetCostAndUsage` | `cost_explorer.get_costs` (`client.get_cost_and_usage(...)`) | Obter custos agrupados por serviço |
| `sts:GetCallerIdentity` | `test_aws.py` (`sts.get_caller_identity()`) | Verificar manualmente a conexão/credenciais |

## Parâmetros da chamada ao Cost Explorer

```python
client.get_cost_and_usage(
    TimePeriod={"Start": <hoje - COST_PERIOD_DAYS dias>, "End": <hoje>},
    Granularity=config.COST_GRANULARITY,   # default "MONTHLY"
    Metrics=[config.COST_METRIC],          # default "UnblendedCost"
    GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
)
```

## Região

- Definida por `config.AWS_REGION` (default `us-east-1`), aplicada em `boto3.client("ce", region_name=...)`.
- Observação técnica: o cliente STS em `test_aws.py` é criado sem região explícita.

## Autenticação: AWS CLI × boto3

O código **não lê nem armazena credenciais**. O boto3 resolve as credenciais pela cadeia padrão da AWS (perfil do AWS CLI configurado via `aws configure`, variáveis de ambiente padrão da AWS, etc.). A docstring de `cost_explorer.py` reforça isso.

## Permissões IAM necessárias (least privilege)

Para o fluxo principal, basta `ce:GetCostAndUsage`. Para o script de verificação, `sts:GetCallerIdentity`.

Exemplo de policy mínima (valores de exemplo):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ce:GetCostAndUsage", "sts:GetCallerIdentity"],
      "Resource": "*"
    }
  ]
}
```

> `ce:GetCostAndUsage` não suporta restrição por recurso específico, por isso `Resource: "*"`. Mantenha a identidade limitada a essas ações.

## Erros de permissão

Se faltar `ce:GetCostAndUsage`, o Cost Explorer retorna `AccessDenied` (ou variantes). `get_costs` detecta esses códigos e levanta `CostExplorerError` com mensagem orientando sobre a permissão. Ver [error-handling.md](error-handling.md).

## Segurança

Nunca inclua Access Key, Secret Key, Account ID real, ARN real ou tokens no repositório. Exemplos nesta documentação usam valores fictícios. O `.env` é ignorado pelo Git.
