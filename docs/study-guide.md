<p align="right"><strong>Português</strong> · <a href="study-guide.en.md">English</a></p>

# Guia de Estudo — AWS Cost Monitor

> Documento técnico voltado a **estudo**. Usa o código real do projeto como
> material didático para explicar os conceitos de **FinOps**, de integração com a
> **AWS** e de **design de software** por trás da ferramenta. A ideia é que, ao
> ler este guia junto com o código, você entenda não só *o que* o projeto faz,
> mas *por que* foi construído assim.

## Índice

1. [O problema: por que monitorar custos na nuvem](#1-o-problema-por-que-monitorar-custos-na-nuvem)
2. [FinOps em uma frase](#2-finops-em-uma-frase)
3. [A regra central: Python calcula, IA interpreta](#3-a-regra-central-python-calcula-ia-interpreta)
4. [Como falamos com a AWS (Cost Explorer + boto3)](#4-como-falamos-com-a-aws-cost-explorer--boto3)
5. [A camada de cálculo determinístico](#5-a-camada-de-cálculo-determinístico)
6. [Regras de FinOps como código](#6-regras-de-finops-como-código)
7. [A camada de IA desacoplada](#7-a-camada-de-ia-desacoplada)
8. [Tratamento de erros como decisão de design](#8-tratamento-de-erros-como-decisão-de-design)
9. [Testes sem tocar na nuvem](#9-testes-sem-tocar-na-nuvem)
10. [Configuração e segredos](#10-configuração-e-segredos)
11. [Exercícios para fixar](#11-exercícios-para-fixar)
12. [Glossário](#12-glossário)

---

## 1. O problema: por que monitorar custos na nuvem

Na nuvem, qualquer pessoa de um time pode criar recursos que geram custo
(instâncias, bancos, storage) sem passar por um processo de compra. Isso é
ótimo para velocidade, mas significa que o gasto cresce de forma difusa:
dezenas de serviços, várias contas, mudanças diárias.

Sem visibilidade, dois problemas aparecem:

- **Desperdício silencioso** — recursos esquecidos ligados, ambientes de teste
  que ninguém desligou, storage antigo acumulando.
- **Surpresa na fatura** — o custo só é percebido quando a conta chega, tarde
  demais para reagir.

A resposta não é "gastar menos a qualquer custo", e sim **enxergar o gasto a
tempo de decidir**. É aí que entra FinOps.

## 2. FinOps em uma frase

> **FinOps** é a prática de trazer responsabilidade financeira para o modelo de
> gasto variável da nuvem, unindo times de engenharia, finanças e negócio para
> tomar decisões com base em dados de custo.

Na prática, FinOps gira em torno de um ciclo:

1. **Informar** — coletar e organizar os custos (quanto, onde, por quê).
2. **Otimizar** — identificar desperdício e oportunidades.
3. **Operar** — agir e repetir continuamente.

Este projeto foca a fase **Informar** (coleta e análise) e dá os primeiros
passos em **Otimizar** (as regras de FinOps que levantam alertas). A fase
**Operar** aparece no roadmap (notificações, agendamento).

## 3. A regra central: Python calcula, IA interpreta

Esta é a decisão de design mais importante do projeto, e vale entender bem
porque ela aparece em quase todos os arquivos.

**O problema que ela resolve:** um modelo de linguagem (LLM) é ótimo para
produzir texto, mas é não-determinístico e pode "alucinar" — inventar um número
que parece plausível. Para dados financeiros, isso é inaceitável: `R$ 1.234,56`
não pode virar `R$ 1.243,65` porque o modelo escorregou.

**A solução:** separar fisicamente as duas responsabilidades.

| Responsabilidade | Onde vive | Propriedade |
|---|---|---|
| Calcular valores | `src/analysis/` (Python puro) | Determinístico, auditável, testável |
| Interpretar valores | `src/ai/` (LLM) | Criativo, substituível, opcional |

A IA **nunca** recebe dados brutos da AWS para somar. Ela recebe números já
prontos e só escreve a leitura em linguagem natural. Veja no `_build_prompt` do
`llama_client.py`: os valores entram já formatados (ex.: `f"{total:.2f} USD"`) e
o prompt instrui explicitamente a *não inventar valores*.

**Por que isso é um bom design, além da precisão:**

- **Testabilidade** — você consegue testar todo o cálculo sem rede e sem IA.
- **Troca de fornecedor** — dá para trocar Llama por OpenAI, Claude ou Bedrock
  sem tocar na lógica de cálculo.
- **Degradação graciosa** — se a IA cair, o número continua certo; só falta a
  interpretação.

> **Conceito transferível:** isole o que precisa ser correto e previsível do que
> precisa ser flexível. Vale para IA, mas também para integrações externas,
> cache, feature flags etc.

## 4. Como falamos com a AWS (Cost Explorer + boto3)

Toda a conversa com a AWS fica em **um único arquivo**: `src/aws/cost_explorer.py`.
É a única parte do código que importa `boto3`. Isso é proposital — concentra a
dependência externa num lugar só.

**Peças envolvidas:**

- **boto3** — o SDK oficial da AWS para Python. Ele não lê credenciais do código:
  procura automaticamente nas credenciais locais (AWS CLI, variáveis de ambiente,
  roles). Por isso o projeto *nunca* carrega chaves no código.
- **AWS Cost Explorer** — o serviço da AWS que expõe os custos. A API usada é
  `get_cost_and_usage`.
- **AWS STS** — serviço de identidade. `get_caller_identity` responde "quem sou
  eu nesta conta?" e serve para validar que as credenciais funcionam
  (`src/test_aws.py`).

**A consulta, em termos conceituais:**

```python
client = boto3.client("ce", region_name=config.AWS_REGION)
client.get_cost_and_usage(
    TimePeriod={"Start": inicio, "End": fim},  # últimos N dias até hoje
    Granularity=config.COST_GRANULARITY,       # MONTHLY
    Metrics=[config.COST_METRIC],              # UnblendedCost
    GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],  # agrupa por serviço
)
```

Três conceitos de custo que vale conhecer:

- **UnblendedCost** — o custo "cru" de cada item, sem média entre contas. É o
  mais direto para analisar o que cada serviço custou.
- **Granularity** — a resolução do tempo: `MONTHLY`, `DAILY` ou `HOURLY`. O
  projeto usa mensal (mais barato de consultar e suficiente para a visão geral).
- **GroupBy SERVICE** — pede à AWS que já quebre o custo por serviço (EC2, S3,
  Lambda...), em vez de um total único.

**Permissão mínima (least privilege):** a identidade só precisa de
`ce:GetCostAndUsage` e `sts:GetCallerIdentity`. Dar só o necessário é um
princípio de segurança — se a credencial vazar, o estrago é limitado.

## 5. A camada de cálculo determinístico

Vive em `src/analysis/cost_analyzer.py`. Duas funções principais, ambas puras
(mesma entrada → mesma saída, sem efeitos colaterais).

### `analyze_costs(costs)`

Transforma a resposta da AWS em um resumo estruturado. Em sequência:

1. Acumula o valor por serviço somando todos os períodos.
2. Soma o total geral.
3. Filtra só os serviços com custo positivo (ignora zeros e créditos).
4. Calcula o percentual de cada serviço — **mas só se o total for positivo**.
5. Acha o serviço de maior custo.

O retorno é um dicionário (`services`, `total_cost`, `percentages`,
`largest_service`...). Retornar **dados estruturados** em vez de texto é o que
permite que a próxima etapa (IA, relatório, testes) consuma o resultado sem
"parsear" strings.

### `compare_periods(costs)` e a divisão por zero

Compara os dois períodos mais recentes para achar a variação percentual. O
detalhe didático está aqui:

```python
if previous_total != 0:
    variation = ((current_total - previous_total) / previous_total) * 100
else:
    variation = None
```

Se o período anterior custou zero, **não existe** variação percentual
(dividir por zero não tem resultado). Em vez de deixar o programa quebrar ou
inventar um número, o código devolve `None` e o relatório mostra "indisponível".

> **Conceito transferível:** trate o caso impossível explicitamente. Um `None`
> honesto é melhor que um número errado ou um crash.

## 6. Regras de FinOps como código

`src/analysis/finops_rules.py` pega os números já calculados e aplica
heurísticas que um analista de FinOps aplicaria "na mão". É **determinístico** —
sem IA, sem rede. A função `generate_alerts` produz três tipos de alerta:

- **Crescimento** — o custo total subiu mais que `FINOPS_GROWTH_THRESHOLD`
  (default 20%) em relação ao período anterior. Sinaliza um salto para investigar.
- **Concentração** — um único serviço representa mais que
  `FINOPS_CONCENTRATION_THRESHOLD` (default 50%) do total. Concentração não é
  necessariamente ruim, mas é um risco a conhecer.
- **Top N** — ranking dos `FINOPS_TOP_N` (default 5) maiores serviços. Puro
  "onde o dinheiro está indo".

Cada alerta é um dicionário com `type`, `severity` e `message`. Note que a
"inteligência" financeira é **Python**, não IA. A IA depois apenas *interpreta*
esses alertas em prosa. Os limiares são configuráveis por variável de ambiente,
então a política de FinOps vira configuração, não código fixo.

## 7. A camada de IA desacoplada

`src/ai/llama_client.py` conversa com um **Llama local** (servidor compatível com
Ollama) via HTTP. O fluxo:

1. `_build_prompt(analysis, comparison, alerts)` monta o texto injetando os
   números já prontos e a instrução de não inventar valores.
2. `interpret(...)` faz um `POST` em `{LLAMA_BASE_URL}/api/generate` com o modelo,
   o prompt e `stream=False`, respeitando `LLAMA_TIMEOUT`.
3. Lê `data["response"]` e devolve a interpretação.

**O ponto de design está no tratamento de falha.** Qualquer coisa que dê errado
— conexão recusada, timeout, HTTP de erro, JSON inválido, resposta vazia — vira
um único `LlamaUnavailableError` com mensagem clara. O orquestrador
(`src/main.py`) captura esse erro e **segue sem a IA**: o relatório sai com os
números corretos e uma nota explicando por que a interpretação faltou.

> **Conceito transferível:** uma dependência opcional deve falhar de forma
> *não-bloqueante*. Pergunte-se sempre: "se isto cair, o que o usuário ainda
> consegue fazer?"

## 8. Tratamento de erros como decisão de design

O projeto não usa `try/except` genérico que engole tudo. Ele converte erros de
baixo nível em **exceções específicas do domínio**:

- Erros do boto3/botocore (credencial ausente, acesso negado) viram
  `CostExplorerError` com uma mensagem que diz o que o usuário precisa fazer.
- Falhas da IA viram `LlamaUnavailableError`.

E o orquestrador decide o que cada erro significa para o *processo*:

- `CostExplorerError` → encerra com código de saída `1` (falha real, não dá para
  continuar sem dados).
- Sem dados no período → código `0` com aviso (não é erro, só não há o que
  mostrar).
- IA indisponível → segue, relatório sem a seção de IA.

> **Conceito transferível:** o código de saída e o tipo de exceção comunicam
> intenção. Um erro de credencial e um "nada a reportar" são situações
> diferentes e merecem respostas diferentes.

## 9. Testes sem tocar na nuvem

A suíte em `tests/` usa `pytest` e **mocks**: ela nunca chama a AWS real nem o
Llama. Isso é possível justamente porque o cálculo é determinístico e as
dependências externas estão isoladas.

O que os testes cobrem:

- Soma do custo total, agrupamento (inclusive acumulando entre períodos).
- Percentuais e identificação do maior serviço.
- Comparação de períodos e o caso de **período anterior zero** (divisão por zero).
- Dados vazios e valores negativos/ajustes.
- As três regras de FinOps (crescimento, concentração, top N).
- O cliente de IA: conexão recusada, timeout, resposta vazia.
- Geração de relatório nos três formatos (txt, JSON, Markdown).

Rodar:

```bash
uv run pytest -v
```

> **Conceito transferível:** código testável e código desacoplado são a mesma
> coisa vista de ângulos diferentes. Se é difícil de testar sem a rede, provavelmente
> está acoplado demais.

## 10. Configuração e segredos

`src/config.py` centraliza toda a parametrização. Lê variáveis de ambiente (via
`python-dotenv`, opcionalmente de um `.env`) e expõe cada parâmetro com um
**default seguro** — então a aplicação roda sem nenhuma configuração.

Regras de ouro de segurança aplicadas no projeto:

- Credenciais da AWS **nunca** no código nem no Git — elas vêm do AWS CLI.
- `.env`, `reports/` e `data/` ficam fora do versionamento (`.gitignore`).
- IAM com menor privilégio.

## 11. Exercícios para fixar

Tente, usando o código como base:

1. **Rastreie um valor.** Pegue o "Custo total" do relatório e siga de onde ele
   veio: qual função o calculou? A partir de qual campo da resposta da AWS?
2. **Quebre de propósito.** Desligue a IA (`AI_ENABLED=false`) e rode. O que muda
   no relatório? Agora deixe a IA ligada com o Llama fora do ar. O resultado é o
   mesmo? Por quê?
3. **Mude uma política.** Baixe `FINOPS_CONCENTRATION_THRESHOLD` para `10`. Que
   alertas novos aparecem? Onde no código esse limiar é lido?
4. **Pense no teste.** Se você adicionasse uma regra "serviço X cresceu mais que
   Y% sozinho", como testaria isso sem chamar a AWS?
5. **Troque o formato.** Rode com `REPORT_FORMAT=json` e depois `markdown`. Os
   números mudam? E a estrutura? Onde está a função que escolhe o formato?

## 12. Glossário

- **FinOps** — disciplina de gestão financeira da nuvem; unir engenharia e
  finanças para decidir com base em dados de custo.
- **Cost Explorer** — serviço da AWS que expõe dados de custo e uso.
- **boto3** — SDK oficial da AWS para Python.
- **STS** — Security Token Service; `get_caller_identity` valida a identidade.
- **UnblendedCost** — custo cru de cada item, sem média entre contas.
- **Granularidade** — resolução temporal da consulta de custo (mensal, diária).
- **IAM / least privilege** — controle de acesso dando só a permissão necessária.
- **Determinístico** — mesma entrada produz sempre a mesma saída.
- **LLM** — Large Language Model (ex.: Llama); gera texto, não é determinístico.
- **Degradação graciosa** — o sistema continua útil mesmo quando uma parte
  opcional falha.
- **Mock** — objeto falso que simula uma dependência externa em testes.

---

> Para o detalhamento arquivo a arquivo, veja os demais documentos em
> [`docs/`](README.md): `architecture.md`, `code-structure.md`, `data-flow.md`,
> `configuration.md`, `aws-permissions.md`, `ai-integration.md`, `reports.md`,
> `error-handling.md`, `testing.md`.
