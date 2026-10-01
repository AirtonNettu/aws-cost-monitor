# Integração com IA — AWS Cost Monitor V1

> Derivado de `src/ai/llama_client.py`, `src/config.py` e `src/main.py`.

## A IA não calcula valores

Ponto central da arquitetura: **a camada de IA não produz nenhum valor financeiro**. Todos os números são calculados por `src/analysis/cost_analyzer.py` (Python). A função `interpret` recebe esses números já prontos e apenas pede uma leitura textual ao modelo.

Isto é visível no código:
- `_build_prompt` formata os valores já calculados (ex.: `f"Custo total do período: {analysis['total_cost']:.2f} USD"`).
- O prompt inicia com: "NÃO invente valores: use somente os números fornecidos."
- O teste `test_prompt_nao_recalcula_usa_valores_fornecidos` verifica que o prompt contém os valores calculados e a instrução de não inventar.

## Como `llama_client.py` funciona

### `interpret(analysis, comparison, alerts=None)`

1. Monta o prompt com `_build_prompt(analysis, comparison, alerts)`.
2. Define a URL: `f"{config.LLAMA_BASE_URL.rstrip('/')}/api/generate"`.
3. Faz `requests.post(url, json={"model": config.LLAMA_MODEL, "prompt": prompt, "stream": False}, timeout=config.LLAMA_TIMEOUT)`.
4. Chama `response.raise_for_status()`.
5. Parseia `response.json()` e extrai `data.get("response")`.
6. Retorna o texto com `.strip()`.

### `_build_prompt(analysis, comparison, alerts=None)`

Monta linhas de texto com: instrução ao modelo (FinOps, não inventar valores, responder em português); custo total; se houver custo positivo, a lista de serviços positivos ordenada desc com valor e percentual, e o maior serviço; caso contrário, a frase de ausência de custo positivo; se `comparison` não for `None`, totais anterior/atual e variação (ou aviso de variação indisponível); quando há `alerts`, a lista de alertas determinísticos já identificados; e um pedido final de apontar maiores custos, mudanças, pontos de atenção e desperdícios.

> Os alertas são determinísticos (gerados por `finops_rules`): o prompt apenas os apresenta ao modelo para interpretação, mantendo a regra "Python calcula, IA interpreta".

## Conexão com o servidor local

- Endpoint: `POST {LLAMA_BASE_URL}/api/generate` (compatível com a API do Ollama).
- Default de `LLAMA_BASE_URL`: `http://localhost:11434`.
- Modelo: `LLAMA_MODEL` (default `llama3`).
- Timeout: `LLAMA_TIMEOUT` segundos (default `60`).

## Tratamento de indisponibilidade

Todas as falhas são convertidas em `LlamaUnavailableError`:

| Situação | Exceção capturada | Mensagem |
|---|---|---|
| Sem conexão | `requests.exceptions.ConnectionError` | "Não foi possível conectar ao Llama em {URL}..." |
| Tempo excedido | `requests.exceptions.Timeout` | "O Llama não respondeu dentro de {timeout}s." |
| Outro erro HTTP | `requests.exceptions.RequestException` | "Falha ao chamar o Llama: {erro}" |
| JSON inválido | `ValueError`/`json.JSONDecodeError` | "Resposta inesperada do Llama (não é um JSON válido)." |
| Campo `response` vazio | — (checagem explícita) | "O Llama respondeu sem conteúdo de interpretação." |

## Comportamento quando a IA não está disponível

Em `src/main.py` (função `run`):
- A IA só é chamada se `config.AI_ENABLED` for verdadeiro.
- Se `interpret` levantar `LlamaUnavailableError`, a mensagem é guardada em `ai_error`, impressa em `stderr` como `[AVISO]`, e o fluxo continua.
- Se `AI_ENABLED` for falso, `ai_error` recebe "Camada de IA desativada por configuração (AI_ENABLED=false)."
- O relatório é gerado de qualquer forma. A indisponibilidade **não interrompe** a execução.

## Como a resposta é usada no relatório

`build_report` recebe `ai_interpretation` e `ai_error`:
- Se `ai_interpretation` existe, é inserido na seção "Interpretação da IA".
- Caso contrário, se `ai_error` existe, a seção mostra "Indisponível. {ai_error}".
- Se nenhum dos dois, mostra "Não solicitada."

## Trocar o provedor

A docstring do módulo indica que trocar o provedor (OpenAI, Claude, Gemini, Bedrock) significa substituir este arquivo. Isso **não está implementado** — hoje só existe o cliente Llama/Ollama. Registrado como contexto de design, não como funcionalidade atual.
