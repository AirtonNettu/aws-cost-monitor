# Tratamento de erros — AWS Cost Monitor V1

> Derivado de `src/aws/cost_explorer.py`, `src/ai/llama_client.py`, `src/analysis/cost_analyzer.py`, `src/reports/report_generator.py` e `src/main.py`.

Formato de cada caso: Problema → Onde é detectado → Como é tratado → Impacto no fluxo.

## Credenciais AWS ausentes/incompletas

- **Onde:** `get_costs`, captura `NoCredentialsError` / `PartialCredentialsError`.
- **Como:** levanta `CostExplorerError("Credenciais da AWS não encontradas ou incompletas. Configure com 'aws configure'...")` com `from exc`.
- **Impacto:** `main.run` captura `CostExplorerError`, imprime `[ERRO]` em stderr e retorna código `1`.

## Permissão insuficiente (AccessDenied)

- **Onde:** `get_costs`, dentro de `except ClientError`, quando o código está em `{AccessDenied, AccessDeniedException, UnauthorizedOperation}`.
- **Como:** levanta `CostExplorerError("Permissão insuficiente... precisa da permissão 'ce:GetCostAndUsage'.")`.
- **Impacto:** `main.run` retorna `1`.

## Outros erros do Cost Explorer

- **Onde:** `get_costs`, `ClientError` com qualquer outro código.
- **Como:** `CostExplorerError(f"O AWS Cost Explorer retornou um erro ({code}): {exc}")`.
- **Impacto:** `main.run` retorna `1`.

## Falha de comunicação com a AWS

- **Onde:** `get_costs`, `except BotoCoreError`.
- **Como:** `CostExplorerError(f"Falha de comunicação com a AWS: {exc}")`.
- **Impacto:** `main.run` retorna `1`.

## Ausência de dados do Cost Explorer

- **Onde:** `main.run`, após `get_costs`, verifica `if not costs`.
- **Como:** imprime `[AVISO]` orientando sobre janela de datas/custos.
- **Impacto:** retorna `0` (sucesso) sem gerar relatório.

## Llama: falha de conexão

- **Onde:** `interpret`, `except requests.exceptions.ConnectionError`.
- **Como:** `LlamaUnavailableError("Não foi possível conectar ao Llama em {URL}...")`.
- **Impacto:** `main.run` captura, grava `ai_error`, imprime `[AVISO]` e **segue**; relatório sai sem interpretação.

## Llama: timeout

- **Onde:** `interpret`, `except requests.exceptions.Timeout`.
- **Como:** `LlamaUnavailableError("O Llama não respondeu dentro de {timeout}s.")`.
- **Impacto:** igual ao caso de conexão; fluxo continua.

## Llama: outro erro HTTP

- **Onde:** `interpret`, `except requests.exceptions.RequestException` (inclui falhas de `raise_for_status`).
- **Como:** `LlamaUnavailableError(f"Falha ao chamar o Llama: {exc}")`.
- **Impacto:** fluxo continua sem interpretação.

## Llama: resposta não-JSON

- **Onde:** `interpret`, `except (ValueError, json.JSONDecodeError)` ao chamar `response.json()`.
- **Como:** `LlamaUnavailableError("Resposta inesperada do Llama (não é um JSON válido).")`.
- **Impacto:** fluxo continua sem interpretação.

## Llama: resposta vazia

- **Onde:** `interpret`, checagem `if not text`.
- **Como:** `LlamaUnavailableError("O Llama respondeu sem conteúdo de interpretação.")`.
- **Impacto:** fluxo continua sem interpretação. Nenhum valor é inventado.

## Dados insuficientes para comparação

- **Onde:** `compare_periods`, `if len(costs) < 2`.
- **Como:** retorna `None`.
- **Impacto:** `build_report` imprime "Não há períodos suficientes para comparação."

## Divisão por zero na variação

- **Onde:** `compare_periods`, `if previous_total != 0 ... else: variation = None`.
- **Como:** não realiza a divisão; `variation = None`.
- **Impacto:** `build_report` imprime "Variação: indisponível (período anterior com custo zero)."

## Ausência de custos positivos

- **Onde:** `analyze_costs` define `has_positive_cost = bool(positive_services)`; `build_report` ramifica nisso.
- **Como:** relatório mostra "Nenhum serviço apresentou custo positivo no período."
- **Impacto:** não lista serviços nem maior serviço; fluxo normal.

## Configuração inteira inválida

- **Onde:** `config._get_int`, ao ler `COST_PERIOD_DAYS` / `LLAMA_TIMEOUT`.
- **Como:** levanta `ValueError(f"A variável de ambiente {name}='{value}' não é um inteiro válido.")`.
- **Impacto:** ocorre na importação de `src.config`; interrompe a execução antes do fluxo. Não é capturado em `main`.

## Geração de relatório

- `build_report` não tem try/except próprio; opera sobre estruturas já validadas pelo analyzer.
- `save_report` cria o diretório com `exist_ok=True` e grava em UTF-8. Erros de IO não são capturados internamente (propagam).

## Observação técnica

Erros de IO em `save_report` e o `ValueError` de configuração não são capturados por `main.run`; propagariam como traceback. Registrado como observação; o código não foi alterado.
