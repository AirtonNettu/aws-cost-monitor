# AWS Cost Monitor — FinOps com IA

Ferramenta de monitoramento e análise de custos da AWS desenvolvida em Python, com foco em práticas de **FinOps**. O projeto consulta os custos da conta através do **AWS Cost Explorer**, organiza os gastos por serviço, executa análises determinísticas em Python e usa uma camada de **IA (Llama local)** para interpretar os resultados e gerar um relatório final.

> **Princípio do projeto:** *Python calcula. IA interpreta.*
> A lógica de cálculo é determinística e vive em Python. A camada de IA é mantida desacoplada do cálculo, de forma que o modelo possa ser trocado (modelo local, OpenAI, Claude, Gemini, Amazon Bedrock) sem alterar a lógica de análise. A IA **nunca** calcula ou inventa valores financeiros: ela recebe os números já calculados e apenas os interpreta.

---

## Sobre o projeto

O AWS Cost Monitor é um projeto de portfólio de **Cloud / FinOps / Python**. A ideia central é separar claramente duas responsabilidades:

1. **Cálculo determinístico** — Python consulta a AWS, soma, filtra e calcula percentuais e variações. Sempre com o mesmo resultado para a mesma entrada.
2. **Interpretação** — uma camada de IA que lê os números já calculados e produz uma leitura em linguagem natural, apontando possíveis desperdícios ou pontos de atenção.

Essa separação é intencional: ela mantém a parte crítica (os números) auditável e previsível, e trata a IA como um componente substituível e opcional.

---

## Objetivo

- Consultar os custos da conta AWS via AWS Cost Explorer.
- Organizar os custos por serviço.
- Realizar análises determinísticas em Python (totais, percentuais, variação entre períodos).
- Interpretar os resultados com uma camada de IA desacoplada.
- Gerar um relatório final a partir dos dados analisados e da interpretação.

---

## Arquitetura

```
AWS Cost Explorer
        ↓
Python / boto3           (coleta de dados)      → src/aws/cost_explorer.py
        ↓
Cost Analyzer            (cálculo determinístico) → src/analysis/cost_analyzer.py
        ↓
Dados estruturados
        ↓
Llama                    (interpretação)         → src/ai/llama_client.py
        ↓
Interpretação
        ↓
Relatório                (geração)               → src/reports/report_generator.py
```

A orquestração do fluxo fica em `src/main.py`, e os parâmetros (região, janela de dias, endpoint do Llama) são centralizados em `src/config.py`.

---

## Fluxo da aplicação

1. `cost_explorer.get_costs()` consulta o AWS Cost Explorer e retorna uma lista de períodos, cada um com os grupos de serviços e seus custos.
2. `cost_analyzer.analyze_costs()` agrupa por serviço, calcula o total, filtra serviços com custo positivo, calcula o percentual de cada um e identifica o serviço de maior custo. **Retorna um dicionário estruturado.**
3. `cost_analyzer.compare_periods()` compara os dois períodos mais recentes e calcula a variação percentual.
4. `llama_client.interpret()` recebe os dados estruturados, monta um prompt com os valores já calculados e pede ao Llama uma interpretação textual. Se o Llama estiver indisponível, levanta um erro claro que o orquestrador trata.
5. `report_generator.build_report()` monta o relatório final (dados + interpretação) e `save_report()` grava um arquivo em `reports/`.

---

## Funcionalidades atuais

- **Verificação de conexão com a AWS** (`src/test_aws.py`): usa o STS `get_caller_identity` para confirmar as credenciais e exibir `Account` e `ARN`.
- **Coleta de custos** (`src/aws/cost_explorer.py`):
  - Cliente Cost Explorer na região configurável (default `us-east-1`).
  - Janela de dias configurável (default 30), granularidade `MONTHLY`, métrica `UnblendedCost`, agrupamento por `SERVICE`.
  - Tratamento explícito de credenciais ausentes/incompletas, permissão insuficiente e erros do Cost Explorer (via `CostExplorerError`).
- **Análise de custos** (`src/analysis/cost_analyzer.py`): agrupamento por serviço, custo total, serviços positivos, percentual por serviço, maior serviço, comparação entre períodos e tratamento seguro de divisão por zero. Todas as funções **retornam dados estruturados**.
- **Interpretação por IA** (`src/ai/llama_client.py`): envia os dados calculados a um Llama local (API compatível com Ollama) e devolve a interpretação. Trata indisponibilidade via `LlamaUnavailableError`, sem mascarar o erro e sem inventar valores.
- **Relatório** (`src/reports/report_generator.py`): monta e salva um relatório organizado com período, total, custo e percentual por serviço, maior serviço, comparação e interpretação da IA (quando disponível).
- **Orquestração** (`src/main.py`): executa o fluxo completo com tratamento de erros em cada etapa.
- **Testes** (`tests/`): suíte com `pytest` e mocks, sem dependência da conta AWS real.

---

## Tecnologias utilizadas

- **Python** `>= 3.14` (ver `.python-version` e `pyproject.toml`)
- **[uv](https://docs.astral.sh/uv/)** — gerenciamento de ambiente e dependências
- **[boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)** — SDK da AWS para Python
- **[requests](https://requests.readthedocs.io/)** — chamada HTTP ao servidor Llama
- **[python-dotenv](https://pypi.org/project/python-dotenv/)** — leitura de configuração via arquivo `.env`
- **[pytest](https://docs.pytest.org/)** — testes (grupo de desenvolvimento)
- **AWS Cost Explorer** / **AWS STS** — consulta de custos e verificação de identidade
- **Llama local** (ex.: [Ollama](https://ollama.com/)) — modelo de interpretação

---

## Estrutura do projeto

```
aws-cost-monitor/
├── src/
│   ├── main.py                 # orquestra o fluxo completo
│   ├── config.py               # configuração centralizada (.env / env vars)
│   ├── test_aws.py             # teste de conexão AWS (STS)
│   ├── aws/
│   │   └── cost_explorer.py    # coleta de custos no Cost Explorer
│   ├── analysis/
│   │   └── cost_analyzer.py    # análise determinística dos custos
│   ├── ai/
│   │   └── llama_client.py     # camada de interpretação por IA (Llama)
│   └── reports/
│       └── report_generator.py # geração/gravação do relatório
├── tests/                      # testes com pytest + mocks
│   ├── conftest.py
│   ├── test_cost_analyzer.py
│   ├── test_llama_client.py
│   └── test_report_generator.py
├── data/.gitkeep               # dados (conteúdo não versionado)
├── reports/.gitkeep            # relatórios gerados (conteúdo não versionado)
├── main.py                     # atalho que delega a src/main.py
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Como funciona a análise de custos

A análise, em `src/analysis/cost_analyzer.py`, é totalmente determinística.

### `analyze_costs(costs)` → `dict`

Retorna `services`, `total_cost`, `positive_services`, `percentages`, `largest_service` e `has_positive_cost`.

1. Acumula o valor (`UnblendedCost.Amount`) por serviço em todos os períodos.
2. Soma o **custo total**.
3. Filtra os **serviços com custo positivo** (valor maior que zero).
4. Se o total for positivo, calcula o **percentual de participação** de cada serviço.
5. Identifica o **serviço de maior custo positivo**.

### `compare_periods(costs)` → `dict | None`

Retorna `None` quando há menos de dois períodos. Caso contrário, devolve `previous_total`, `current_total` e `variation`.

### Tratamento de divisão por zero

Quando o período anterior tem custo total **igual a zero**, não é possível calcular variação percentual. A aplicação **não tenta a divisão** e define a variação como `None`:

```python
if previous_total != 0:
    variation = ((current_total - previous_total) / previous_total) * 100
else:
    variation = None
```

---

## Integração com AWS Cost Explorer

A coleta está em `src/aws/cost_explorer.py` e usa `boto3`:

- **Cliente:** `boto3.client("ce", region_name=config.AWS_REGION)` (default `us-east-1`)
- **Período (`TimePeriod`):** dos últimos `COST_PERIOD_DAYS` dias (default 30) até a data atual.
- **Granularidade:** `MONTHLY` · **Métrica:** `UnblendedCost` · **Agrupamento:** dimensão `SERVICE`

A função percorre `ResultsByTime` e organiza cada período com `start`, `end`, `estimated` e `groups`. Erros são convertidos em `CostExplorerError` com mensagens claras.

---

## Configuração da AWS

1. **Configure o AWS CLI** com suas credenciais:

    ```bash
    aws configure
    ```

    O boto3 usará automaticamente as credenciais configuradas.

2. **Permissões IAM (menor privilégio).** A identidade precisa apenas de:
    - `ce:GetCostAndUsage`
    - `sts:GetCallerIdentity`

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

> **Nunca** coloque Access Key, Secret Key ou qualquer credencial no repositório.

---

## Instalação

Pré-requisitos: [uv](https://docs.astral.sh/uv/getting-started/installation/) e Python 3.14+.

```bash
git clone <url-do-repositorio>
cd aws-cost-monitor

# Ambiente + dependências (inclui o grupo de dev com pytest)
uv sync --dev
```

---

## Configuração do ambiente

As credenciais AWS vêm da configuração local do AWS CLI. Os demais parâmetros são lidos de variáveis de ambiente (opcionalmente de um arquivo `.env` na raiz, carregado via `python-dotenv`). Todos têm defaults seguros — a aplicação roda sem `.env`.

| Variável           | Default                  | Descrição                                            |
|--------------------|--------------------------|------------------------------------------------------|
| `AWS_REGION`       | `us-east-1`              | Região do cliente Cost Explorer                      |
| `COST_PERIOD_DAYS` | `30`                     | Janela de análise em dias                            |
| `COST_GRANULARITY` | `MONTHLY`                | Granularidade da consulta                            |
| `COST_METRIC`      | `UnblendedCost`          | Métrica de custo                                     |
| `AI_ENABLED`       | `true`                   | Liga/desliga a camada de IA                          |
| `LLAMA_BASE_URL`   | `http://localhost:11434` | Endpoint do servidor Llama (compatível com Ollama)   |
| `LLAMA_MODEL`      | `llama3`                 | Nome do modelo                                       |
| `LLAMA_TIMEOUT`    | `60`                     | Timeout (segundos) da chamada ao Llama               |
| `REPORTS_DIR`      | `reports`                | Pasta onde os relatórios são salvos                  |

Exemplo de `.env` (não versionado):
```env
AWS_REGION=us-east-1
COST_PERIOD_DAYS=30
AI_ENABLED=true
LLAMA_BASE_URL=http://localhost:11434
LLAMA_MODEL=llama3
```

> A camada de IA é opcional. Com `AI_ENABLED=false`, ou com o Llama fora do ar, o relatório é gerado normalmente, apenas sem a interpretação (o motivo fica registrado no relatório).

---

## Execução

**Fluxo completo** (coleta → análise → IA → relatório):
```bash
uv run python -m src.main
# ou, pelo atalho da raiz:
uv run python main.py
```

**Verificar a conexão com a AWS:**
```bash
uv run python src/test_aws.py
```

**Rodar só a coleta ou só a análise** (útil para depuração):
```bash
uv run python -m src.aws.cost_explorer
uv run python -m src.analysis.cost_analyzer
```

---

## Exemplos de saída

> Valores **ilustrativos**. A saída real depende da sua conta AWS.

Verificação de conexão (`test_aws.py`):
```
AWS conectada com sucesso
Account: 123456789012
ARN: arn:aws:iam::123456789012:user/exemplo
```

Relatório final (`src/main.py`):
```
============================================================
AWS COST MONITOR — RELATÓRIO DE CUSTOS
============================================================
Gerado em: 2026-10-01 14:30:00
Período analisado: 2026-09-01 a 2026-10-01

Custo total: 50.00 USD

Custo por serviço:
  - Amazon EC2: 30.00 USD (60.0%)
  - Amazon S3: 10.00 USD (20.0%)
  - AWS Lambda: 10.00 USD (20.0%)

Maior serviço: Amazon EC2

------------------------------------------------------------
Comparação entre períodos:
  Período anterior: 0.00 USD
  Período atual:    50.00 USD
  Variação: indisponível (período anterior com custo zero).

------------------------------------------------------------
Interpretação da IA:
  Indisponível. Não foi possível conectar ao Llama em http://localhost:11434. ...
============================================================
```

---

## Segurança

- **Nunca** armazenar credenciais AWS no Git.
- Fornecer credenciais via **AWS CLI** / variáveis de ambiente.
- Aplicar **IAM com menor privilégio**.
- **Não versionar** o arquivo `.env` nem dados/relatórios potencialmente sensíveis.

O `.gitignore` já impede o versionamento de:
```
.venv/            # ambiente virtual
__pycache__/      # cache do Python
*.pyc             # arquivos compilados
.env              # variáveis de ambiente / segredos
reports/*         # relatórios gerados (mantém apenas .gitkeep)
data/*            # dados coletados (mantém apenas .gitkeep)
```

---

## Testes

Os testes usam `pytest` e **mocks**, sem tocar na conta AWS real nem no Llama. Cobrem a lógica crítica: custo total, agrupamento (inclusive acumulado entre períodos), percentuais, maior serviço, comparação de períodos, período anterior zero (divisão por zero), dados vazios, valores negativos/ajustes, cliente de IA (conexão/timeout/resposta vazia) e geração de relatório.

```bash
uv run pytest -v
```

---

## Roadmap

### Já implementado (V1)

- [x] Ambiente Python com `uv`.
- [x] Verificação de conexão com a AWS via STS.
- [x] Coleta de custos no Cost Explorer com parâmetros configuráveis.
- [x] Análise determinística retornando dados estruturados (total, positivos, %, maior serviço).
- [x] Comparação entre períodos com tratamento de divisão por zero.
- [x] Camada de IA (Llama) desacoplada, com tratamento de indisponibilidade.
- [x] Geração e gravação de relatório.
- [x] Orquestração do fluxo completo em `src/main.py`.
- [x] Configuração centralizada em `src/config.py` (via `.env`).
- [x] Tratamento de erros em todas as etapas.
- [x] Suíte de testes com mocks.

### Em desenvolvimento / planejado

- [ ] Identificação automática de desperdícios com regras determinísticas (além da IA).
- [ ] Sistema de alertas.
- [ ] Suporte a outros provedores de IA (OpenAI, Claude, Gemini, Bedrock).
- [ ] Formatos de relatório adicionais (Markdown, JSON, HTML).
- [ ] Evolução para arquitetura serverless (Lambda, EventBridge, SNS, CloudWatch).
- [ ] Execução automatizada / agendada.

---

## Próximos passos

1. Adicionar regras determinísticas de detecção de desperdício (ex.: variação acima de um limiar).
2. Abstrair a camada de IA em uma interface para suportar múltiplos provedores.
3. Oferecer saída do relatório em Markdown/JSON.

---

## Limitações atuais

- A interpretação depende de um **Llama local** em execução; sem ele, o relatório sai sem a seção de IA (comportamento esperado e tratado).
- A granularidade é mensal e a janela é baseada em dias corridos a partir de hoje.
- Não há persistência histórica dos relatórios além dos arquivos `.txt` em `reports/`.
- A detecção de "desperdício" hoje vem apenas da interpretação da IA, não de regras determinísticas.

---

## Autor

**José Airton de Carvalho Neto**

Projeto de portfólio de Cloud / FinOps / Python.

- GitHub: [@AirtonNettu](https://github.com/AirtonNettu)
- LinkedIn: [jose-airton-cloud](https://www.linkedin.com/in/jose-airton-cloud/)
