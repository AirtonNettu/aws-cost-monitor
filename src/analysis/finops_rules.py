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


def _check_anomaly_spikes(daily_costs: list[float] | None = None) -> dict | None:
    """Detecta picos de gastos anômalos usando Z-score estatístico e razão sobre mediana.

    Exige no mínimo 5 amostras para relevância estatística.
    """
    if not daily_costs or len(daily_costs) < 5:
        return None

    mean = sum(daily_costs) / len(daily_costs)
    if mean <= 0:
        return None

    variance = sum((x - mean) ** 2 for x in daily_costs) / (len(daily_costs) - 1)
    std_dev = variance ** 0.5
    if std_dev == 0:
        return None

    max_val = max(daily_costs)
    z_score = (max_val - mean) / std_dev

    # Para amostras pequenas (ex: 5 a 14 dias), o Z-score máximo teórico é sqrt(N-1) <= 2.23
    # Então checamos Z >= 2.0 ou razão >= 2.5x da média dos demais dias
    outros = [x for x in daily_costs if x != max_val]
    media_outros = sum(outros) / len(outros) if outros else mean

    eh_spike = (z_score >= 2.0 or (media_outros > 0 and max_val >= 2.5 * media_outros)) and (max_val - media_outros) > 5.0

    if eh_spike:
        severity = "critical" if (z_score >= 2.2 or max_val >= 3.0 * media_outros) else "warning"
        return {
            "type": "anomaly",
            "severity": severity,
            "message": (
                f"Pico anômalo detectado: gasto pontual de {max_val:.2f} USD "
                f"(desvio expressivo vs média diária de {media_outros:.2f} USD)."
            ),
        }
    return None


def generate_alerts(analysis, comparison, daily_costs: list[float] | None = None):
    """Gera a lista de alertas de FinOps a partir dos dados calculados.

    Parâmetros
    ----------
    analysis : dict
        Saída de ``cost_analyzer.analyze_costs``.
    comparison : dict | None
        Saída de ``cost_analyzer.compare_periods``.
    daily_costs : list[float] | None
        Série temporal de custos diários para detecção estatística de anomalias.

    Retorno
    -------
    list[dict]
        Lista (possivelmente vazia) de alertas. Vazia quando não há custo
        positivo ou nenhuma regra foi acionada.
    """
    alerts = []

    anomaly = _check_anomaly_spikes(daily_costs)
    if anomaly:
        alerts.append(anomaly)

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

    untagged = _check_untagged(analysis)
    if untagged:
        alerts.append(untagged)

    return alerts


def _check_untagged(analysis, threshold=10.0):
    """Alerta quando recursos sem tag (Untagged) superam o limiar do custo total."""
    percentages = analysis.get("percentages", {})
    for item, pct in percentages.items():
        if "untagged" in item.lower() and pct >= threshold:
            return {
                "type": "untagged_resources",
                "severity": "warning",
                "message": (
                    f"Recursos sem tag ('{item}') representam {pct:.1f}% do custo "
                    f"total (limiar: {threshold:.1f}%). Boas práticas de FinOps "
                    f"recomendam taguear todos os recursos para alocação precisa."
                ),
            }
    return None

