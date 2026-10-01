"""Regras determinísticas de FinOps.

Princípio do projeto: Python calcula, IA interpreta.
Este módulo aplica regras determinísticas sobre os dados já calculados pelo
``cost_analyzer`` e produz uma lista de alertas estruturados. Não faz rede,
não chama a IA e não recalcula valores financeiros: apenas deriva observações
a partir dos números recebidos.

Cada alerta é um dict com:
    - type: identificador da regra ("growth", "concentration", "top_services")
    - severity: "info" | "warning"
    - message: texto pronto para exibição
"""

from src import config


def _check_growth(comparison, threshold):
    """Alerta quando o custo total cresce acima do limiar entre períodos."""
    if comparison is None:
        return None
    variation = comparison.get("variation")
    if variation is None:
        return None
    if variation > threshold:
        return {
            "type": "growth",
            "severity": "warning",
            "message": (
                f"Custo total cresceu {variation:.1f}% em relação ao período "
                f"anterior (limiar: {threshold:.1f}%)."
            ),
        }
    return None


def _check_concentration(analysis, threshold):
    """Alerta quando um único serviço concentra mais que o limiar do total."""
    percentages = analysis.get("percentages", {})
    if not percentages:
        return None
    service, pct = max(percentages.items(), key=lambda item: item[1])
    if pct > threshold:
        return {
            "type": "concentration",
            "severity": "warning",
            "message": (
                f"O serviço '{service}' concentra {pct:.1f}% do custo total "
                f"(limiar: {threshold:.1f}%)."
            ),
        }
    return None


def _top_services(analysis, top_n):
    """Informa os N serviços de maior custo positivo."""
    positive = analysis.get("positive_services", {})
    if not positive:
        return None
    ranking = sorted(positive.items(), key=lambda item: item[1], reverse=True)
    top = ranking[:top_n]
    itens = ", ".join(f"{service} ({amount:.2f} USD)" for service, amount in top)
    return {
        "type": "top_services",
        "severity": "info",
        "message": f"Top {len(top)} serviços por custo: {itens}.",
    }


def generate_alerts(analysis, comparison):
    """Gera a lista de alertas de FinOps a partir dos dados calculados.

    Parâmetros
    ----------
    analysis : dict
        Saída de ``cost_analyzer.analyze_costs``.
    comparison : dict | None
        Saída de ``cost_analyzer.compare_periods``.

    Retorno
    -------
    list[dict]
        Lista (possivelmente vazia) de alertas. Vazia quando não há custo
        positivo ou nenhuma regra foi acionada.
    """
    alerts = []

    growth = _check_growth(comparison, config.FINOPS_GROWTH_THRESHOLD)
    if growth:
        alerts.append(growth)

    concentration = _check_concentration(
        analysis, config.FINOPS_CONCENTRATION_THRESHOLD
    )
    if concentration:
        alerts.append(concentration)

    top = _top_services(analysis, config.FINOPS_TOP_N)
    if top:
        alerts.append(top)

    return alerts
