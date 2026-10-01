# Estrutura do código — AWS Cost Monitor V1

> Derivado do código real. Nomes de funções, parâmetros e retornos conferidos nos arquivos-fonte.

## Estrutura real de diretórios

```text
aws-cost-monitor/
├── src/
│   ├── __init__.py
│   ├── main.py                 # orquestração do fluxo
│   ├── config.py               # configuração via env/.env
│   ├── test_aws.py             # verificação de conexão (STS)
│   ├── aws/
│   │   ├── __init__.py
│   │   └── cost_explorer.py    # coleta no Cost Explorer
│   ├── analysis/
│   │   ├── __init__.py
│   │   └── cost_analyzer.py    # cálculo determinístico
│   ├── ai/
│   │   ├── __init__.py
│   │   └── llama_client.py     # interpretação via Llama
│   └── reports/
│       ├── __init__.py
│       └── report_generator.py # montagem/gravação do relatório
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_cost_analyzer.py
│   ├── test_llama_client.py
│   └── test_report_generator.py
├── data/.gitkeep
├── reports/.gitkeep
├── main.py                     # atalho que chama src.main.main
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .python-version
└── README.md
```

---

## `src/config.py`

- **Finalidade:** centralizar parâmetros lidos de variáveis de ambiente.
- **Dependências:** `os`, `dotenv.load_dotenv`.
- **Processamento:** chama `load_dotenv()` na importação; define constantes de módulo.
- **Função `_get_int(name, default)`:** lê a env como inteiro; retorna o default se ausente/vazia; levanta `ValueError` se não for inteiro válido.
- **Saídas (constantes):** `AWS_REGION`, `COST_PERIOD_DAYS`, `COST_GRANULARITY`, `COST_METRIC`, `LLAMA_BASE_URL`, `LLAMA_MODEL`, `LLAMA_TIMEOUT`, `AI_ENABLED`, `REPORTS_DIR`.
- **Relação:** importado por `cost_explorer.py`, `llama_client.py`, `report_generator.py` e `main.py`.

Detalhes de cada variável em [configuration.md](configuration.md).

---

## `src/aws/cost_explorer.py`

- **Responsabilidade:** única camada que fala com a AWS; coleta e organiza, sem calcular.
- **Dependências:** `datetime` (`date`, `timedelta`), `boto3`, `botocore.exceptions`, `src.config`.
- **Classe `CostExplorerError(Exception)`:** erro de alto nível com mensagem amigável.
- **Função `get_costs(period_days=None)`:**
  - **Entrada:** `period_days` opcional; usa `config.COST_PERIOD_DAYS` se `None`.
  - **boto3:** `boto3.client("ce", region_name=config.AWS_REGION)` e `client.get_cost_and_usage(...)`.
  - **Período:** `start_date = date.today() - timedelta(days=period_days)`, `end_date = date.today()`, enviados em ISO.
  - **Métrica/agrupamento:** `Metrics=[config.COST_METRIC]`, `GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]`, `Granularity=config.COST_GRANULARITY`.
  - **Exceções tratadas:** `NoCredentialsError`/`PartialCredentialsError`; `ClientError` (distingue `AccessDenied`/`AccessDeniedException`/`UnauthorizedOperation` dos demais); `BotoCoreError`. Todas viram `CostExplorerError` com `raise ... from exc`.
  - **Saída:** `list[dict]`, um item por período com `start`, `end`, `estimated`, `groups`.
- **Relação:** consumido por `cost_analyzer.py` e por `main.py`.

---

## `src/analysis/cost_analyzer.py`

- **Responsabilidade:** cálculo determinístico. Não faz rede nem IA.
- **Dependências:** nenhuma externa (usa só built-ins).
- **Função `_sum_period(period)`:** soma `float(UnblendedCost.Amount)` dos grupos de um período.
- **Função `analyze_costs(costs)`:**
  - **Entrada:** lista de períodos (saída de `get_costs`).
  - **Processamento:** acumula por serviço (`services`); soma `total_cost`; filtra `positive_services` (valor `> 0`); calcula `percentages` apenas se `total_cost > 0`; define `largest_service` via `max(positive_services, key=...)` ou `None`.
  - **Saída:** dict com `services`, `total_cost`, `positive_services`, `percentages`, `largest_service`, `has_positive_cost`.
- **Função `compare_periods(costs)`:**
  - **Entrada:** lista de períodos.
  - **Processamento:** retorna `None` se `len(costs) < 2`; soma os totais do penúltimo e do último; calcula variação percentual, ou `None` quando o total anterior é `0`.
  - **Saída:** dict com `previous_total`, `current_total`, `variation`, ou `None`.
- **Relação:** consome `get_costs`; alimenta `llama_client` e `report_generator`.

---

## `src/ai/llama_client.py`

- **Responsabilidade:** interpretar os dados calculados via Llama local. Não calcula valores.
- **Dependências:** `json`, `requests`, `src.config`.
- **Classe `LlamaUnavailableError(Exception)`:** servidor indisponível ou resposta inválida.
- **Função `_build_prompt(analysis, comparison)`:** monta o texto do prompt com os valores já calculados e formatados; inclui a instrução de não inventar valores. Retorna `str`.
- **Função `interpret(analysis, comparison)`:**
  - **Entrada:** dicts de `analyze_costs` e `compare_periods` (este pode ser `None`).
  - **Processamento:** `POST {LLAMA_BASE_URL}/api/generate` com `model`, `prompt`, `stream=False`, `timeout=LLAMA_TIMEOUT`; `raise_for_status()`; parseia JSON; lê `response`.
  - **Exceções:** `ConnectionError`, `Timeout`, `RequestException`, JSON inválido e `response` vazio viram `LlamaUnavailableError`.
  - **Saída:** `str` (texto do modelo, com `.strip()`).
- **Relação:** chamado por `main.py` quando `AI_ENABLED`.

---

## `src/reports/report_generator.py`

- **Responsabilidade:** transformar dados + interpretação em relatório; gravar em disco.
- **Dependências:** `os`, `datetime.datetime`, `src.config`.
- **Função `_format_period(costs)`:** retorna `"{start} a {end}"` do primeiro e último período, ou `"Nenhum período disponível"` se vazio.
- **Função `_money(value)`:** arredonda para 2 casas e normaliza o zero (inclusive `-0.0`) para `0.00`. Retorna `str`.
- **Função `build_report(costs, analysis, comparison, ai_interpretation=None, ai_error=None)`:** monta o texto completo. Ramos: com/sem custo positivo; comparação `None` vs. presente; variação `None` vs. valor; IA presente / erro / não solicitada. Retorna `str`.
- **Função `save_report(report_text, directory=None)`:** cria o diretório (default `config.REPORTS_DIR`), grava `report_<timestamp>.txt` em UTF-8, retorna o caminho.
- **Relação:** chamado por `main.py`.

---

## `src/main.py`

- **Responsabilidade:** orquestrar o fluxo.
- **Dependências:** `sys`, `src.config`, e as funções/exceções dos demais módulos.
- **Função `run()`:** coleta (trata `CostExplorerError`, retorna `1`); se não há dados, avisa e retorna `0`; analisa e compara; se `AI_ENABLED`, tenta `interpret` (captura `LlamaUnavailableError`); monta e imprime o relatório; salva e imprime o caminho; retorna `0`.
- **Função `main()`:** `sys.exit(run())`.
- **Relação:** topo da cadeia; `main.py` da raiz o invoca.

---

## `main.py` (raiz)

Atalho: importa `from src.main import main` e o executa em `__main__`.

---

## `src/test_aws.py`

Script de verificação manual: cria `boto3.client("sts")`, chama `get_caller_identity()` e imprime `Account` e `Arn`. Não é importado pelo fluxo principal e não trata exceções.
