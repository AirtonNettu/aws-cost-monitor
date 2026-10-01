# Relatórios — AWS Cost Monitor V1

> Derivado de `src/reports/report_generator.py` e `src/main.py`.

## Quem gera

`src/reports/report_generator.py`:
- `build_report(...)` monta o relatório em **texto**.
- `build_report_json(...)` monta em **JSON**.
- `build_report_markdown(...)` monta em **Markdown**.
- `build_report_for_format(report_format, ...)` seleciona o builder e retorna `(texto, formato_normalizado)`.
- `save_report(...)` grava em disco com a extensão correta.

São chamadas por `src/main.py` (função `run`), que escolhe o formato por `config.REPORT_FORMAT`.

## Formatos

O formato é definido por `REPORT_FORMAT` (`txt` default, `json` ou `markdown`). Formato desconhecido cai em `txt`. A extensão do arquivo segue `_FORMAT_EXTENSIONS`: `txt` → `.txt`, `json` → `.json`, `markdown` → `.md`.

Os três formatos derivam dos **mesmos dados determinísticos**; mudam apenas a apresentação.

### Texto (`.txt`)

Texto puro em UTF-8. Separadores de largura fixa: `"=" * 60` nas bordas e `"-" * 60` entre seções. Estrutura:

```text
============================================================
AWS COST MONITOR — RELATÓRIO DE CUSTOS
============================================================
Gerado em: <YYYY-MM-DD HH:MM:SS>
Período analisado: <start> a <end>

Custo total: <valor> USD

Custo por serviço:
  - <serviço>: <valor> USD (<pct>%)
  ...

Maior serviço: <serviço>

------------------------------------------------------------
Comparação entre períodos:
  Período anterior: <valor> USD
  Período atual:    <valor> USD
  Variação: <pct>%

------------------------------------------------------------
Alertas de FinOps:
  - [SEVERITY] <mensagem>
  (ou "Nenhum alerta gerado.")

------------------------------------------------------------
Interpretação da IA:
<texto da IA, ou mensagem de indisponível/não solicitada>
============================================================
```

### JSON (`.json`)

`build_report_json` serializa um objeto com: `generated_at`, `period`, `total_cost`, `has_positive_cost`, `largest_service`, `services` (dict), `percentages` (dict), `comparison` (objeto ou `null`), `alerts` (lista), `ai_interpretation` e `ai_error`. Usa `json.dumps(..., ensure_ascii=False, indent=2)`. Valores monetários passam por `_round_money` (zero negativo normalizado para `0.0`).

### Markdown (`.md`)

`build_report_markdown` produz um documento com título, metadados em lista, uma **tabela** de custo por serviço, e seções "Comparação entre períodos", "Alertas de FinOps" e "Interpretação da IA".

## Localização

`save_report` grava em `config.REPORTS_DIR` (default `reports/`), criando o diretório com `os.makedirs(..., exist_ok=True)`. Nome do arquivo: `report_<YYYYMMDD_HHMMSS>.<ext>`, com `ext` conforme o formato (`txt`/`json`/`md`). Retorna o caminho, que `main.py` imprime.

> O `.gitignore` ignora `reports/*` (exceto `.gitkeep`), portanto relatórios gerados não são versionados.

## Informações incluídas

- Data/hora de geração (`datetime.now()`).
- Período analisado (`_format_period`: `"{start} a {end}"`, ou "Nenhum período disponível").
- Custo total.
- Custo e percentual por serviço (apenas quando há custo positivo), ordenado desc por valor.
- Maior serviço (quando há custo positivo).
- Comparação entre períodos.
- Alertas de FinOps (ou "Nenhum alerta gerado.").
- Interpretação da IA (ou mensagem de indisponibilidade/não solicitada).

## Seção de alertas de FinOps

Os alertas vêm de `finops_rules.generate_alerts` (ver [architecture.md](architecture.md) e [code-structure.md](code-structure.md)). No texto aparecem como `- [SEVERITY] mensagem`; no Markdown como item com severidade em negrito; no JSON como a lista `alerts` (cada item com `type`, `severity`, `message`). Quando a lista está vazia, o texto/Markdown mostram "Nenhum alerta gerado." e o JSON traz `[]`.

## Tratamento de valores

### Normalização de `-0.00` — `_round_money()` e `_money()`

```python
def _round_money(value, places=2):
    rounded = round(float(value), places)
    if rounded == 0:
        rounded = 0.0
    return rounded


def _money(value):
    return f"{_round_money(value):.2f}"
```

`_round_money` arredonda e, se o resultado for zero (incluindo `-0.0` ou valores minúsculos que arredondam para zero), força `0.0`. `_money` formata como string de 2 casas para o texto/Markdown; `_round_money` é usado nos valores numéricos do JSON. Isso evita saídas como `-0.00 USD` ou `"total_cost": -0.0`.

### Custo zero / sem custo positivo

Quando `analysis["has_positive_cost"]` é falso, o relatório imprime "Nenhum serviço apresentou custo positivo no período." e **não** lista serviços nem maior serviço.

### Valores negativos / ajustes

`analyze_costs` soma valores negativos no total e nos `services`, mas só considera positivos (`> 0`) em `positive_services`, percentuais e maior serviço. Assim, créditos/ajustes negativos influenciam o total, mas não aparecem como serviços de custo. (Verificado por `test_valor_negativo_nao_entra_em_positivos`.)

## Comportamento da seção de IA

Decidido por `build_report`:
- `ai_interpretation` presente → mostra o texto.
- senão `ai_error` presente → "Indisponível. {ai_error}".
- senão → "Não solicitada."

Nos testes, `build_report` é chamado com `ai_interpretation` e `ai_error` diretamente, validando os três ramos (ver [testing.md](testing.md)).
