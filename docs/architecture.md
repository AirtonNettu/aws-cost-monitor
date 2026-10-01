# Arquitetura — AWS Cost Monitor V1

> Documento derivado do código real do repositório. Descreve como o sistema funciona hoje, não funcionalidades planejadas.

## Objetivo técnico

O AWS Cost Monitor coleta custos da conta AWS via **AWS Cost Explorer**, executa cálculos determinísticos em Python (totais, percentuais, maior serviço, variação entre períodos) e, opcionalmente, envia os números já calculados a um modelo **Llama local** para obter uma interpretação textual. O resultado é consolidado em um relatório `.txt` salvo em disco.

## Regra arquitetural: Python calcula, IA interpreta

A separação é concreta no código:

- **Cálculo** vive em `src/analysis/cost_analyzer.py`. Todas as funções são determinísticas e retornam dicionários. Nenhuma chamada de rede ou IA ocorre aqui.
- **Interpretação** vive em `src/ai/llama_client.py`. A função `interpret(analysis, comparison)` recebe os dicionários já calculados e, em `_build_prompt`, injeta os valores prontos no texto enviado ao modelo. O prompt instrui explicitamente: "NÃO invente valores: use somente os números fornecidos."
- O modelo nunca recebe dados brutos da AWS nem é solicitado a calcular. Ele só lê números já formatados (ex.: `f"{analysis['total_cost']:.2f} USD"`).

Consequência técnica: a camada de IA pode ficar indisponível ou ser trocada por outro provedor sem afetar os valores financeiros, que são produzidos exclusivamente pelo Python.

## Componentes e responsabilidades

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| Configuração | `src/config.py` | Lê variáveis de ambiente (via `python-dotenv`) e expõe parâmetros com defaults. |
| Coleta AWS | `src/aws/cost_explorer.py` | Única camada que fala com a AWS. Consulta o Cost Explorer e organiza a resposta. Define `CostExplorerError`. |
| Análise | `src/analysis/cost_analyzer.py` | Cálculo determinístico. `analyze_costs` e `compare_periods`. |
| Regras de FinOps | `src/analysis/finops_rules.py` | Alertas determinísticos (crescimento, concentração, top N). `generate_alerts`. |
| IA | `src/ai/llama_client.py` | Interpretação textual via Llama local. `interpret`, `_build_prompt`, `LlamaUnavailableError`. |
| Relatório | `src/reports/report_generator.py` | Monta e grava o relatório em txt/json/markdown. `build_report`, `build_report_json`, `build_report_markdown`, `build_report_for_format`, `save_report`. |
| Orquestração | `src/main.py` | Encadeia coleta → análise → comparação → IA → relatório. |
| Atalho raiz | `main.py` | Importa e chama `src.main.main`. |
| Teste de conexão | `src/test_aws.py` | Script independente que valida credenciais via STS `get_caller_identity`. |

## Fluxo geral

```text
AWS Cost Explorer
       ↓
src/aws/cost_explorer.py        get_costs() -> list[dict]
       ↓
src/analysis/cost_analyzer.py   analyze_costs() -> dict
                                compare_periods() -> dict | None
       ↓
src/analysis/finops_rules.py    generate_alerts() -> list[dict]
       ↓
src/ai/llama_client.py          interpret() -> str   (opcional)
       ↓
src/reports/report_generator.py build_report_for_format() -> (str, fmt); save_report() -> path
       ↓
reports/report_<timestamp>.(txt|json|md)
```

Orquestração em `src/main.py` (função `run`).

## Integração com AWS

- Cliente boto3: `boto3.client("ce", region_name=config.AWS_REGION)`.
- API chamada: `get_cost_and_usage`.
- Parâmetros: `TimePeriod` (hoje menos `COST_PERIOD_DAYS` dias até hoje), `Granularity=config.COST_GRANULARITY`, `Metrics=[config.COST_METRIC]`, `GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]`.
- Autenticação: delegada ao boto3, que usa as credenciais locais (AWS CLI / variáveis de ambiente). Nenhuma credencial é lida no código.

## Camada de análise

`analyze_costs(costs)` acumula `UnblendedCost.Amount` por serviço em todos os períodos, soma o total, filtra serviços com valor `> 0`, calcula percentuais (apenas quando `total_cost > 0`) e identifica o maior serviço positivo. Retorna um dicionário com `services`, `total_cost`, `positive_services`, `percentages`, `largest_service`, `has_positive_cost`.

`compare_periods(costs)` compara os dois últimos períodos. Retorna `None` se houver menos de dois. A variação é `None` quando o total anterior é zero (evita divisão por zero).

## Regras determinísticas de FinOps

`generate_alerts(analysis, comparison)` aplica três regras sobre os dados já calculados e retorna uma lista de alertas (`type`, `severity`, `message`): crescimento do custo total acima de `FINOPS_GROWTH_THRESHOLD`, concentração de um serviço acima de `FINOPS_CONCENTRATION_THRESHOLD`, e ranking "top N" (`FINOPS_TOP_N`). É determinístico: não usa IA nem rede. Reforça a regra arquitetural — a "inteligência" financeira também é Python. Os alertas entram no relatório e no prompt da IA (que apenas os interpreta).

## Camada de IA

`interpret(analysis, comparison, alerts=None)` monta o prompt com `_build_prompt` (incluindo os alertas, quando houver) e faz `POST` em `{LLAMA_BASE_URL}/api/generate` com `{"model": LLAMA_MODEL, "prompt": ..., "stream": False}` e `timeout=LLAMA_TIMEOUT`. Lê `data["response"]`. Qualquer falha (conexão, timeout, HTTP, JSON inválido, resposta vazia) vira `LlamaUnavailableError`.

## Geração de relatório

`build_report_for_format(config.REPORT_FORMAT, ...)` seleciona o builder conforme o formato (`txt`/`json`/`markdown`; desconhecido cai em `txt`) e retorna `(texto, formato)`. Os três builders derivam dos mesmos dados determinísticos (incluindo os alertas). `save_report(..., report_format=...)` cria o diretório (default `reports/`) e grava `report_<YYYYMMDD_HHMMSS>.<ext>` em UTF-8, com extensão por formato.

## Tratamento de erros

- Coleta: exceções do boto3/botocore são convertidas em `CostExplorerError` com mensagens específicas (credenciais, acesso negado, outros erros).
- IA: falhas viram `LlamaUnavailableError`; `src/main.py` captura e segue sem interpretação.
- Orquestração: `CostExplorerError` encerra com código de saída `1`; ausência de dados encerra com `0` e aviso.

Detalhes em [error-handling.md](error-handling.md).

## Decisões arquiteturais identificadas no código

- **Desacoplamento IA/cálculo** (docstrings de `cost_analyzer.py` e `llama_client.py`): a IA só interpreta.
- **Config centralizada com defaults** (`src/config.py`): a aplicação roda sem `.env`.
- **IA opcional e não-bloqueante** (`src/main.py`): a indisponibilidade do Llama não impede o relatório.
- **Camada AWS isolada** (`cost_explorer.py`): é a única que importa boto3.
- **`pythonpath = ["."]`** no `pyproject.toml`: permite os imports `from src...` ao rodar como módulo e nos testes.

## Observações técnicas (não corrigidas — apenas registradas)

- `COST_GRANULARITY=MONTHLY` com uma janela de 30 dias pode retornar um ou dois períodos dependendo de onde a janela cai no mês; `compare_periods` só compara quando há dois ou mais.
- `src/test_aws.py` cria o cliente STS sem a região do config e não trata exceções (é um script de verificação manual, não parte do fluxo de `main`).
