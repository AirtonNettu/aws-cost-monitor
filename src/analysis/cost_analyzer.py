"""Análise determinística dos custos coletados no AWS Cost Explorer.

Princípio do projeto: Python calcula, IA interpreta.
Todas as funções deste módulo são determinísticas e retornam estruturas de
dados (não imprimem). A camada de IA e a de relatório consomem esses retornos.
"""


def _sum_period(period):
    """Soma o UnblendedCost de todos os grupos de um período."""
    return sum(
        float(group["Metrics"]["UnblendedCost"]["Amount"])
        for group in period["groups"]
    )


def analyze_costs(costs):
    """Agrupa os custos por serviço e calcula totais, percentuais e maior serviço.

    Parâmetros
    ----------
    costs : list[dict]
        Lista de períodos retornada por ``cost_explorer.get_costs``.

    Retorno
    -------
    dict com as chaves:
        - services: dict {serviço: custo acumulado}
        - total_cost: float
        - positive_services: dict {serviço: custo} apenas valores > 0
        - percentages: dict {serviço: percentual de participação no total}
        - largest_service: str | None (serviço de maior custo positivo)
        - has_positive_cost: bool
    """
    services = {}

    for period in costs:
        for group in period["groups"]:
            service = group["Keys"][0]
            amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
            services[service] = services.get(service, 0.0) + amount

    total_cost = sum(services.values())

    positive_services = {
        service: amount for service, amount in services.items() if amount > 0
    }

    percentages = {}
    if total_cost > 0:
        for service, amount in positive_services.items():
            percentages[service] = (amount / total_cost) * 100

    largest_service = (
        max(positive_services, key=positive_services.get)
        if positive_services
        else None
    )

    return {
        "services": services,
        "total_cost": total_cost,
        "positive_services": positive_services,
        "percentages": percentages,
        "largest_service": largest_service,
        "has_positive_cost": bool(positive_services),
    }


def compare_periods(costs):
    """Compara os dois períodos mais recentes e calcula a variação percentual.

    Retorno
    -------
    dict | None
        None quando não há períodos suficientes (< 2). Caso contrário:
        - previous_total: float
        - current_total: float
        - variation: float | None  (None quando o período anterior é zero,
          evitando divisão por zero)
    """
    if len(costs) < 2:
        return None

    previous_period = costs[-2]
    current_period = costs[-1]

    previous_total = _sum_period(previous_period)
    current_total = _sum_period(current_period)

    if previous_total != 0:
        variation = ((current_total - previous_total) / previous_total) * 100
    else:
        variation = None

    return {
        "previous_total": previous_total,
        "current_total": current_total,
        "variation": variation,
    }


if __name__ == "__main__":
    from src.aws.cost_explorer import get_costs

    costs = get_costs()
    print(analyze_costs(costs))
    print(compare_periods(costs))
