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
│   │   ├── cost_analyzer.py    # cálculo determinístico
│   │   └── finops_rules.py     # regras determinísticas de FinOps (alertas)
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
│   ├── test_finops_rules.py
│   ├── test_llama_client.py
│   ├── test_report_formats.py
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
- **Função `_get_float(name, default)`:** idem para float.
- **Saídas (constantes):** `AWS_REGION`, `COST_PERIOD_DAYS`, `COST_GRANULARITY`, `COST_METRIC`, `LLAMA_BASE_URL`, `LLAMA_MODEL`, `LLAMA_TIMEOUT`, `AI_ENABLED`, `FINOPS_GROWTH_THRESHOLD`, `FINOPS_CONCENTRATION_THRESHOLD`, `FINOPS_TOP_N`, `REPORT_FORMAT`, `REPORTS_DIR`.
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
- **Relação:** consome `get_costs`; alimenta `finops_rules`, `llama_client` e `report_generator`.

---

## `src/analysis/finops_rules.py`

- **Responsabilidade:** aplicar regras determinísticas sobre os dados calculados e produzir alertas. Não faz rede nem IA.
- **Dependências:** `src.config`.
- **Função `_check_growth(comparison, threshold)`:** retorna um alerta `growth` (severity `warning`) quando `comparison["variation"]` existe e supera o limiar; senão `None` (inclui `comparison is None` e `variation is None`).
- **Função `_check_concentration(analysis, threshold)`:** pega o serviço de maior percentual; se passar do limiar, retorna alerta `concentration` (`warning`); senão `None`.
- **Função `_top_services(analysis, top_n)`:** retorna alerta `top_services` (`info`) com os N maiores serviços positivos; `None` se não há positivos.
- **Função `generate_alerts(analysis, comparison)`:** orquestra as três regras e retorna `list[dict]` (possivelmente vazia). Cada alerta tem `type`, `severity`, `message`.
- **Relação:** chamado por `main.run`; os alertas vão para `report_generator` e para o prompt de `llama_client`.

---

## `src/ai/llama_client.py`

- **Responsabilidade:** interpretar os dados calculados via Llama local. Não calcula valores.
- **Dependências:** `json`, `requests`, `src.config`.
- **Classe `LlamaUnavailableError(Exception)`:** servidor indisponível ou resposta inválida.
- **Função `_build_prompt(analysis, comparison, alerts=None)`:** monta o texto do prompt com os valores já calculados e formatados; inclui a instrução de não inventar valores e, quando há `alerts`, lista os alertas determinísticos. Retorna `str`.
- **Função `interpret(analysis, comparison, alerts=None)`:**
  - **Entrada:** dicts de `analyze_costs` e `compare_periods` (este pode ser `None`); lista opcional de alertas.
  - **Processamento:** `POST {LLAMA_BASE_URL}/api/generate` com `model`, `prompt`, `stream=False`, `timeout=LLAMA_TIMEOUT`; `raise_for_status()`; parseia JSON; lê `response`.
  - **Exceções:** `ConnectionError`, `Timeout`, `RequestException`, JSON inválido e `response` vazio viram `LlamaUnavailableError`.
  - **Saída:** `str` (texto do modelo, com `.strip()`).
- **Relação:** chamado por `main.py` quando `AI_ENABLED`.

---

## `src/reports/report_generator.py`

- **Responsabilidade:** transformar dados + interpretação em relatório; gravar em disco.
- **Dependências:** `os`, `datetime.datetime`, `src.config`.
- **Função `_format_period(costs)`:** retorna `"{start} a {end}"` do primeiro e último período, ou `"Nenhum período disponível"` se vazio.
- **Função `_round_money(value, places=2)`:** arredonda e normaliza o zero negativo para `0.0` (retorna número).
- **Função `_money(value)`:** usa `_round_money` e formata como string com 2 casas (`"0.00"`).
- **Função `build_report(costs, analysis, comparison, ai_interpretation=None, ai_error=None, alerts=None)`:** monta o relatório **texto**. Ramos: com/sem custo positivo; comparação `None` vs. presente; variação `None` vs. valor; seção de alertas; IA presente / erro / não solicitada. Retorna `str`.
- **Função `build_report_json(...)`:** mesmos dados em **JSON** (string indentada, `ensure_ascii=False`), com `total_cost`, `services`, `percentages`, `comparison`, `alerts`, `ai_interpretation`, `ai_error`. Valores monetários normalizados por `_round_money`.
- **Função `build_report_markdown(...)`:** mesmos dados em **Markdown** (cabeçalho, tabela de serviços, seções de comparação, alertas e IA).
- **Função `build_report_for_format(report_format, *args, **kwargs)`:** normaliza o formato, seleciona o builder (`_BUILDERS`) e retorna `(texto, formato_normalizado)`; formato desconhecido cai em `txt`.
- **Função `save_report(report_text, directory=None, report_format="txt")`:** cria o diretório (default `config.REPORTS_DIR`), grava `report_<timestamp>.<ext>` (ext por `_FORMAT_EXTENSIONS`: `txt`/`json`/`md`) em UTF-8, retorna o caminho.
- **Relação:** chamado por `main.py`.

---

## `src/main.py`

- **Responsabilidade:** orquestrar o fluxo.
- **Dependências:** `sys`, `src.config`, e as funções/exceções dos demais módulos.
- **Função `run()`:** coleta (trata `CostExplorerError`, retorna `1`); se não há dados, avisa e retorna `0`; analisa e compara; gera alertas com `generate_alerts`; se `AI_ENABLED`, tenta `interpret(analysis, comparison, alerts)` (captura `LlamaUnavailableError`); monta o relatório via `build_report_for_format(config.REPORT_FORMAT, ...)`, imprime, salva com a extensão correta e imprime o caminho; retorna `0`.
- **Função `main()`:** `sys.exit(run())`.
- **Relação:** topo da cadeia; `main.py` da raiz o invoca.

---

## `main.py` (raiz)

Atalho: importa `from src.main import main` e o executa em `__main__`.

---

## `src/test_aws.py`

Script de verificação manual: cria `boto3.client("sts")`, chama `get_caller_identity()` e imprime `Account` e `Arn`. Não é importado pelo fluxo principal e não trata exceções.
