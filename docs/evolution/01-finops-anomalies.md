# Fase 1: Detecção Estatística de Anomalias & Previsão de Fatura

Nesta fase, o `aws-cost-monitor` deixa de apenas olhar para o passado e passa a **detectar picos anormais de gasto em tempo real** e **projetar quanto a fatura vai fechar no fim do mês**.

---

## 1. Por que isso torna o projeto de nível sênior?
Ferramentas básicas de nuvem apenas mostram quanto foi gasto ontem.
Ferramentas profissionais de FinOps avisam:
> *"Atenção: O serviço Amazon RDS gastou US$ 14,20 hoje, o que está 3 desvios-padrão acima da média dos últimos 14 dias (US$ 2,50/dia). Projeção de fechar o mês em US$ 420 em vez de US$ 75."*

Isso salva empresas de pagarem faturas de milhares de reais por esquecerem instâncias ligadas.

---

## 2. A Matemática: Python Puro, Sem Dependências Pesadas

Em vez de usar bibliotecas gigantes de Machine Learning (como Scikit-Learn ou TensorFlow), usamos **estatística determinística em Python puro** (`statistics.mean` e `statistics.stdev`), mantendo o pacote Lambda leve (< 100 KB) e rápido (< 1s).

### O Algoritmo de Anomalia (Z-Score):
Seja $X$ a série de custos dos últimos $N$ dias para um serviço:
1. Média: $\mu = \frac{\sum X}{N}$
2. Desvio-Padrão: $\sigma = \sqrt{\frac{\sum (X - \mu)^2}{N}}$
3. Z-Score do dia atual: $Z = \frac{CustoHoje - \mu}{\sigma}$

- **Se $Z > 2.5$:** Dispara Alerta de **Anomalia Crítica** (gasto estatisticamente improvável).
- **Se $Z > 1.8$:** Dispara Alerta de **Atenção (Warning)**.

---

## 3. Algoritmo de Projeção do Fim do Mês (Month-End Forecast)

```python
import calendar
from datetime import date


def forecast_monthly_cost(current_cost: float, day_of_month: int) -> float:
    """Projeta o custo total do mês baseado no gasto diário até hoje."""
    today = date.today()
    _, total_days_in_month = calendar.monthrange(today.year, today.month)

    if day_of_month <= 0:
        return current_cost

    daily_burn_rate = current_cost / day_of_month
    projected_total = daily_burn_rate * total_days_in_month
    return round(projected_total, 2)
```

---

## 4. Onde Integrar no Código Existente
1. Em `src/database/repository.py`: Adicionar função `get_daily_costs_history(days=14)` lendo do banco SQLite `data/costs.db`.
2. Em `src/analysis/finops_rules.py`: Adicionar a regra `_check_anomalies(history, current_costs)`.
3. No relatório HTML e no Streamlit: Exibir um card com:
   - **Gasto Atual:** US$ 25.00
   - **Projeção Fim do Mês:** US$ 77.50
   - **Status de Anomalia:** 🟢 Normal ou 🔴 Pico Detectado
