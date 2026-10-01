"""Geração do relatório final de custos.

Responsabilidade única: transformar os dados já calculados (analyzer) e a
interpretação da IA (quando disponível) em um relatório legível. Não calcula
valores nem chama a AWS/IA diretamente.
"""

import os
from datetime import datetime

from src import config


def _format_period(costs):
    """Retorna uma string com o intervalo coberto pelos períodos coletados."""
    if not costs:
        return "Nenhum período disponível"
    start = costs[0]["start"]
    end = costs[-1]["end"]
    return f"{start} a {end}"


def _money(value):
    """Formata um valor monetário com 2 casas.

    Normaliza o zero negativo (ex.: -0.0 ou valores minúsculos que arredondam
    para zero) para "0.00", evitando saídas como "-0.00 USD".
    """
    rounded = round(float(value), 2)
    if rounded == 0:
        rounded = 0.0
    return f"{rounded:.2f}"


def build_report(
    costs,
    analysis,
    comparison,
    ai_interpretation=None,
    ai_error=None,
    alerts=None,
):
    """Monta o texto do relatório a partir dos dados calculados.

    Parâmetros
    ----------
    costs : list[dict]
        Períodos coletados (para exibir o intervalo analisado).
    analysis : dict
        Saída de ``cost_analyzer.analyze_costs``.
    comparison : dict | None
        Saída de ``cost_analyzer.compare_periods``.
    ai_interpretation : str | None
        Texto da IA, se disponível.
    ai_error : str | None
        Mensagem explicando por que a IA não está disponível, se for o caso.
    alerts : list[dict] | None
        Alertas determinísticos de ``finops_rules.generate_alerts``.

    Retorno
    -------
    str
        O relatório formatado.
    """
    linhas = []
    linhas.append("=" * 60)
    linhas.append("AWS COST MONITOR — RELATÓRIO DE CUSTOS")
    linhas.append("=" * 60)
    linhas.append(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    linhas.append(f"Período analisado: {_format_period(costs)}")
    linhas.append("")

    linhas.append(f"Custo total: {_money(analysis['total_cost'])} USD")
    linhas.append("")

    if analysis["has_positive_cost"]:
        linhas.append("Custo por serviço:")
        for service, amount in sorted(
            analysis["positive_services"].items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            pct = analysis["percentages"].get(service, 0.0)
            linhas.append(f"  - {service}: {_money(amount)} USD ({pct:.1f}%)")
        linhas.append("")
        linhas.append(f"Maior serviço: {analysis['largest_service']}")
    else:
        linhas.append("Nenhum serviço apresentou custo positivo no período.")
    linhas.append("")

    linhas.append("-" * 60)
    linhas.append("Comparação entre períodos:")
    if comparison is None:
        linhas.append("  Não há períodos suficientes para comparação.")
    else:
        linhas.append(
            f"  Período anterior: {_money(comparison['previous_total'])} USD"
        )
        linhas.append(
            f"  Período atual:    {_money(comparison['current_total'])} USD"
        )
        if comparison["variation"] is not None:
            linhas.append(f"  Variação: {comparison['variation']:.1f}%")
        else:
            linhas.append(
                "  Variação: indisponível (período anterior com custo zero)."
            )
    linhas.append("")

    linhas.append("-" * 60)
    linhas.append("Alertas de FinOps:")
    if alerts:
        for alert in alerts:
            linhas.append(f"  - [{alert['severity'].upper()}] {alert['message']}")
    else:
        linhas.append("  Nenhum alerta gerado.")
    linhas.append("")

    linhas.append("-" * 60)
    linhas.append("Interpretação da IA:")
    if ai_interpretation:
        linhas.append(ai_interpretation)
    elif ai_error:
        linhas.append(f"  Indisponível. {ai_error}")
    else:
        linhas.append("  Não solicitada.")
    linhas.append("=" * 60)

    return "\n".join(linhas)


def save_report(report_text, directory=None):
    """Salva o relatório em um arquivo .txt com timestamp e retorna o caminho."""
    directory = directory or config.REPORTS_DIR
    os.makedirs(directory, exist_ok=True)
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(report_text)
    return path
