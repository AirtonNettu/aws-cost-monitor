# Testes — AWS Cost Monitor V1

> Derivado dos arquivos em `tests/` e da configuração em `pyproject.toml`.

## Framework e execução

- Framework: **pytest** (`pytest>=8.0.0`, no grupo `dev` do `pyproject.toml`).
- Configuração em `pyproject.toml`:
  ```toml
  [tool.pytest.ini_options]
  pythonpath = ["."]
  testpaths = ["tests"]
  ```
  `pythonpath = ["."]` permite os imports `from src...`; `testpaths = ["tests"]` restringe a coleta.
- Execução:
  ```bash
  uv run pytest -v
  ```
- Estado atual: **39 passed**. Os testes não acessam a AWS real nem um servidor Llama real.

## Estrutura

```text
tests/
├── __init__.py
├── conftest.py                 # fixtures de dados fictícios
├── test_cost_analyzer.py       # 10 testes
├── test_finops_rules.py        # 8 testes
├── test_llama_client.py        # 5 testes
├── test_report_formats.py      # 11 testes
└── test_report_generator.py    # 5 testes
```

## Fixtures (`conftest.py`)

Helpers `_group(service, amount)` e `_period(start, end, groups, estimated=False)` montam dados no formato do Cost Explorer. Fixtures:

- `costs_single_period`: um período com Amazon S3 (10), Amazon EC2 (30), AWS Lambda (10).
- `costs_two_periods`: dois períodos de Amazon S3 (100 e 150).
- `costs_previous_zero`: período anterior com 0 e atual com 50.
- `costs_empty`: período sem grupos.
- `costs_with_negative`: Amazon EC2 (40) e Refund (-10).

## `test_cost_analyzer.py` (10)

Valida a lógica determinística:
- `test_total_cost`: total 50.0.
- `test_agrupamento_por_servico`: dict de serviços esperado.
- `test_agrupamento_acumula_entre_periodos`: S3 soma 100+150 = 250.
- `test_percentual_por_servico`: EC2 60%, S3 20%, soma 100%.
- `test_maior_servico`: EC2.
- `test_dados_vazios`: total 0, dicts vazios, `largest_service` None, `has_positive_cost` False.
- `test_valor_negativo_nao_entra_em_positivos`: total 30; "Refund" fora de positivos; maior é EC2.
- `test_comparacao_entre_periodos`: anterior 100, atual 150, variação 50%.
- `test_comparacao_periodo_anterior_zero`: anterior 0, variação None (divisão por zero evitada).
- `test_comparacao_periodos_insuficientes`: `compare_periods` retorna None com 1 período.

## `test_llama_client.py` (5)

Usa `monkeypatch` para substituir `llama_client.requests.post` por um fake (classe `_FakeResponse`). Nenhuma chamada HTTP real.
- `test_interpret_retorna_texto`: resposta `{"response": "Interpretação gerada."}` → retorna o texto.
- `test_interpret_erro_de_conexao`: `ConnectionError` → `LlamaUnavailableError`.
- `test_interpret_timeout`: `Timeout` → `LlamaUnavailableError`.
- `test_interpret_resposta_sem_conteudo`: `{"response": ""}` → `LlamaUnavailableError`.
- `test_prompt_nao_recalcula_usa_valores_fornecidos`: o prompt contém "50.00 USD", "Amazon EC2" e "NÃO invente valores".

## `test_finops_rules.py` (8)

Valida as regras determinísticas (`generate_alerts` e helpers), usando as fixtures e `monkeypatch` sobre `config`:
- sem custo positivo não gera alertas;
- concentração dispara alerta (EC2 = 60% > 50%);
- `top_services` presente quando há custo positivo;
- crescimento acima do limiar dispara (100→150 = +50%);
- crescimento abaixo do limiar não dispara (limiar elevado via `monkeypatch`);
- sem comparação não gera `growth`;
- `variation` None (período anterior zero) não gera `growth`;
- `FINOPS_TOP_N=1` limita o ranking a um serviço.

## `test_report_formats.py` (11)

Valida JSON, Markdown e o seletor de formato (sem rede; usa `tmp_path` para o teste de gravação):
- estrutura do JSON (total, serviços, maior serviço, alertas, comparação);
- JSON com comparação e com `variation` None;
- JSON sem custo positivo;
- Markdown contém as seções e a tabela de serviços;
- Markdown sem custo positivo;
- seletor para `json` e `markdown` (com normalização de espaços/maiúsculas);
- formato desconhecido cai em `txt`; default (`None`) é `txt` e igual a `build_report`;
- `save_report` grava com a extensão correta por formato (`.txt`/`.json`/`.md`).

## `test_report_generator.py` (5)

Chama `build_report` diretamente, sem IO de rede nem gravação em disco:
- `test_relatorio_com_custo_positivo`: contém "Custo total: 50.00 USD", "Amazon EC2", "Maior serviço: Amazon EC2".
- `test_relatorio_sem_custo_positivo`: contém "Nenhum serviço apresentou custo positivo".
- `test_relatorio_inclui_interpretacao_da_ia`: insere o texto da IA passado.
- `test_relatorio_registra_ia_indisponivel`: mostra "Indisponível" e a mensagem de erro.
- `test_relatorio_comparacao_zero_anterior`: mostra "indisponível (período anterior com custo zero)".

## Mocks utilizados

- `monkeypatch.setattr(llama_client.requests, "post", fake_post)` substitui a chamada HTTP.
- Dados do Cost Explorer são simulados pelas fixtures (não há mock do boto3 porque o analyzer e o relatório não chamam a AWS).

## O que não é testado

- `src/aws/cost_explorer.py` (`get_costs` e o tratamento de `CostExplorerError`) — não há teste automatizado; depende de boto3/AWS.
- `src/main.py` (`run`/`main`) — orquestração não coberta por teste.
- `src/config.py` (`_get_int`/`_get_float` e parsing de env) — sem teste dedicado (embora `config` seja manipulado via `monkeypatch` em alguns testes de FinOps).
- `src/test_aws.py` — é um script manual, não um teste pytest.

> `save_report` passou a ter cobertura (extensão por formato) em `test_report_formats.py`.

Registrado como estado real da cobertura, sem alteração de código.
