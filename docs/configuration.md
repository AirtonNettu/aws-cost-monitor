# Configuração — AWS Cost Monitor V1

> Todas as variáveis abaixo existem em `src/config.py`. Nenhuma foi inventada.

A configuração é carregada na importação de `src/config.py`, que chama `load_dotenv()` (lê um arquivo `.env` na raiz, se existir) e então lê variáveis de ambiente. Todas têm default — a aplicação roda sem `.env`.

Inteiros são lidos por `_get_int(name, default)`: usa o default se a variável estiver ausente ou vazia; levanta `ValueError` se o valor existir mas não for um inteiro válido.

`AI_ENABLED` é interpretada como verdadeira quando o valor (sem espaços, minúsculo) está em `{"1", "true", "yes"}`.

## Variáveis

| Variável | Finalidade | Default | Onde é usada | Se não definida |
|---|---|---|---|---|
| `AWS_REGION` | Região do cliente boto3 do Cost Explorer | `us-east-1` | `cost_explorer.get_costs` (`boto3.client("ce", region_name=...)`) | Usa `us-east-1` |
| `COST_PERIOD_DAYS` | Janela de análise em dias (hoje menos N dias) | `30` | `cost_explorer.get_costs` (`timedelta(days=...)`) | Usa `30` |
| `COST_GRANULARITY` | Granularidade da consulta | `MONTHLY` | `cost_explorer.get_costs` (`Granularity=...`) | Usa `MONTHLY` |
| `COST_METRIC` | Métrica de custo consultada | `UnblendedCost` | `cost_explorer.get_costs` (`Metrics=[...]`) | Usa `UnblendedCost` |
| `LLAMA_BASE_URL` | URL base do servidor Llama | `http://localhost:11434` | `llama_client.interpret` (`POST {url}/api/generate`) | Usa `http://localhost:11434` |
| `LLAMA_MODEL` | Nome do modelo | `llama3` | `llama_client.interpret` (campo `model`) | Usa `llama3` |
| `LLAMA_TIMEOUT` | Timeout (s) da chamada ao Llama | `60` | `llama_client.interpret` (`timeout=...`) | Usa `60` |
| `AI_ENABLED` | Liga/desliga a camada de IA | `true` | `main.run` (decide se chama `interpret`) | Considerada `true` |
| `FINOPS_GROWTH_THRESHOLD` | Crescimento (%) do custo total que dispara alerta | `20.0` | `finops_rules._check_growth` | Usa `20.0` |
| `FINOPS_CONCENTRATION_THRESHOLD` | Participação (%) de um serviço que dispara alerta | `50.0` | `finops_rules._check_concentration` | Usa `50.0` |
| `FINOPS_TOP_N` | Qtde de serviços no ranking "top N" | `5` | `finops_rules._top_services` | Usa `5` |
| `REPORT_FORMAT` | Formato do relatório (`txt`/`json`/`markdown`) | `txt` | `main.run` → `report_generator.build_report_for_format` | Usa `txt`; valor desconhecido também cai em `txt` |
| `REPORTS_DIR` | Diretório de saída dos relatórios | `reports` | `report_generator.save_report` | Usa `reports` |

> `FINOPS_GROWTH_THRESHOLD` e `FINOPS_CONCENTRATION_THRESHOLD` são lidas por `_get_float`; `FINOPS_TOP_N` por `_get_int`. Valor não-numérico levanta `ValueError` na importação de `src.config`.

> Observação técnica: embora a tabela do `COST_METRIC` seja configurável, `cost_analyzer._sum_period` e `analyze_costs` leem especificamente `Metrics["UnblendedCost"]["Amount"]`. Mudar `COST_METRIC` sem ajustar o analyzer pode gerar `KeyError`. Isto é registrado apenas como observação; o código não foi alterado.

## Credenciais AWS

Não há variável de credencial no `config.py`. O boto3 obtém as credenciais da configuração local (AWS CLI / variáveis de ambiente padrão da AWS). Ver [aws-permissions.md](aws-permissions.md).

## Exemplo de `.env` (valores fictícios, não versionado)

```env
AWS_REGION=us-east-1
COST_PERIOD_DAYS=30
COST_GRANULARITY=MONTHLY
COST_METRIC=UnblendedCost
AI_ENABLED=true
LLAMA_BASE_URL=http://localhost:11434
LLAMA_MODEL=llama3
LLAMA_TIMEOUT=60
REPORTS_DIR=reports
```

O `.gitignore` ignora `.env`, portanto ele não é versionado.
