# Relatórios — AWS Cost Monitor V1

> Derivado de `src/reports/report_generator.py` e `src/main.py`.

## Quem gera

`src/reports/report_generator.py`:
- `build_report(...)` monta o texto.
- `save_report(...)` grava em disco.

São chamadas por `src/main.py` (função `run`).

## Formato

Texto puro (`.txt`), em UTF-8. Separadores de largura fixa: `"=" * 60` nas bordas e `"-" * 60` entre seções. Estrutura:

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
Interpretação da IA:
<texto da IA, ou mensagem de indisponível/não solicitada>
============================================================
```

## Localização

`save_report` grava em `config.REPORTS_DIR` (default `reports/`), criando o diretório com `os.makedirs(..., exist_ok=True)`. Nome do arquivo: `report_<YYYYMMDD_HHMMSS>.txt`. Retorna o caminho, que `main.py` imprime.

> O `.gitignore` ignora `reports/*` (exceto `.gitkeep`), portanto relatórios gerados não são versionados.

## Informações incluídas

- Data/hora de geração (`datetime.now()`).
- Período analisado (`_format_period`: `"{start} a {end}"`, ou "Nenhum período disponível").
- Custo total.
- Custo e percentual por serviço (apenas quando há custo positivo), ordenado desc por valor.
- Maior serviço (quando há custo positivo).
- Comparação entre períodos.
- Interpretação da IA (ou mensagem de indisponibilidade/não solicitada).

## Tratamento de valores

### Normalização de `-0.00` — função `_money()`

A função existe no código:

```python
def _money(value):
    rounded = round(float(value), 2)
    if rounded == 0:
        rounded = 0.0
    return f"{rounded:.2f}"
```

Arredonda para 2 casas e, se o resultado arredondado for zero (incluindo `-0.0` ou valores minúsculos que arredondam para zero), força `0.0`, evitando a saída `-0.00 USD`. É aplicada ao custo total, ao custo por serviço e aos totais anterior/atual da comparação.

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
