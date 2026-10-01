"""Geração do relatório final de custos.

Responsabilidade única: transformar os dados já calculados (analyzer) e a
interpretação da IA (quando disponível) em um relatório legível. Não calcula
valores nem chama a AWS/IA diretamente.
"""

import json
import os
from datetime import datetime

from src import config

# Extensão de arquivo por formato de relatório.
_FORMAT_EXTENSIONS = {"txt": "txt", "json": "json", "markdown": "md"}


def _format_period(costs):
    """Retorna uma string com o intervalo coberto pelos períodos coletados."""
    if not costs:
        return "Nenhum período disponível"
    start = costs[0]["start"]
    end = costs[-1]["end"]
    return f"{start} a {end}"


def _round_money(value, places=2):
    """Arredonda um valor monetário normalizando o zero negativo para 0.0."""
    rounded = round(float(value), places)
    if rounded == 0:
        rounded = 0.0
    return rounded


def _money(value):
    """Formata um valor monetário com 2 casas.

    Normaliza o zero negativo (ex.: -0.0 ou valores minúsculos que arredondam
    para zero) para "0.00", evitando saídas como "-0.00 USD".
    """
    return f"{_round_money(value):.2f}"


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


def build_report_json(
    costs,
    analysis,
    comparison,
    ai_interpretation=None,
    ai_error=None,
    alerts=None,
):
    """Monta o relatório como JSON (string) a partir dos dados calculados.

    Estrutura pensada para integração (ex.: consumo programático / V2 serverless).
    Os mesmos dados determinísticos do relatório .txt, em formato estruturado.

    Retorno
    -------
    str
        JSON formatado (indentado, UTF-8 preservado).
    """
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "period": _format_period(costs),
        "total_cost": _round_money(analysis["total_cost"]),
        "has_positive_cost": analysis["has_positive_cost"],
        "largest_service": analysis["largest_service"],
        "services": {
            service: _round_money(amount)
            for service, amount in analysis["positive_services"].items()
        },
        "percentages": {
            service: round(float(pct), 1)
            for service, pct in analysis["percentages"].items()
        },
        "comparison": None,
        "alerts": alerts or [],
        "ai_interpretation": ai_interpretation,
        "ai_error": ai_error,
    }

    if comparison is not None:
        payload["comparison"] = {
            "previous_total": _round_money(comparison["previous_total"]),
            "current_total": _round_money(comparison["current_total"]),
            "variation": (
                round(float(comparison["variation"]), 1)
                if comparison["variation"] is not None
                else None
            ),
        }

    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_report_markdown(
    costs,
    analysis,
    comparison,
    ai_interpretation=None,
    ai_error=None,
    alerts=None,
):
    """Monta o relatório em Markdown (string) a partir dos dados calculados."""
    linhas = []
    linhas.append("# AWS Cost Monitor — Relatório de Custos")
    linhas.append("")
    linhas.append(f"- **Gerado em:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    linhas.append(f"- **Período analisado:** {_format_period(costs)}")
    linhas.append(f"- **Custo total:** {_money(analysis['total_cost'])} USD")
    linhas.append("")

    linhas.append("## Custo por serviço")
    if analysis["has_positive_cost"]:
        linhas.append("")
        linhas.append("| Serviço | Custo (USD) | Participação |")
        linhas.append("|---|---|---|")
        for service, amount in sorted(
            analysis["positive_services"].items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            pct = analysis["percentages"].get(service, 0.0)
            linhas.append(f"| {service} | {_money(amount)} | {pct:.1f}% |")
        linhas.append("")
        linhas.append(f"**Maior serviço:** {analysis['largest_service']}")
    else:
        linhas.append("")
        linhas.append("Nenhum serviço apresentou custo positivo no período.")
    linhas.append("")

    linhas.append("## Comparação entre períodos")
    linhas.append("")
    if comparison is None:
        linhas.append("Não há períodos suficientes para comparação.")
    else:
        linhas.append(
            f"- Período anterior: {_money(comparison['previous_total'])} USD"
        )
        linhas.append(
            f"- Período atual: {_money(comparison['current_total'])} USD"
        )
        if comparison["variation"] is not None:
            linhas.append(f"- Variação: {comparison['variation']:.1f}%")
        else:
            linhas.append(
                "- Variação: indisponível (período anterior com custo zero)."
            )
    linhas.append("")

    linhas.append("## Alertas de FinOps")
    linhas.append("")
    if alerts:
        for alert in alerts:
            linhas.append(f"- **[{alert['severity'].upper()}]** {alert['message']}")
    else:
        linhas.append("Nenhum alerta gerado.")
    linhas.append("")

    linhas.append("## Interpretação da IA")
    linhas.append("")
    if ai_interpretation:
        linhas.append(ai_interpretation)
    elif ai_error:
        linhas.append(f"_Indisponível._ {ai_error}")
    else:
        linhas.append("_Não solicitada._")

    return "\n".join(linhas)


# Mapa formato normalizado -> função construtora.
_BUILDERS = {
    "txt": build_report,
    "json": build_report_json,
    "markdown": build_report_markdown,
}


def build_report_for_format(report_format, *args, **kwargs):
    """Seleciona o builder conforme o formato e retorna (texto, formato_normalizado).

    O formato é normalizado (sem espaços, minúsculo). Formato desconhecido cai
    em "txt" como fallback seguro.
    """
    fmt = (report_format or "txt").strip().lower()
    builder = _BUILDERS.get(fmt)
    if builder is None:
        fmt = "txt"
        builder = build_report
    return builder(*args, **kwargs), fmt


def save_report(report_text, directory=None, report_format="txt"):
    """Salva o relatório com a extensão correta e retorna o caminho.

    A extensão é derivada de ``report_format`` ("txt" -> .txt, "json" -> .json,
    "markdown" -> .md). Formato desconhecido usa .txt.
    """
    directory = directory or config.REPORTS_DIR
    os.makedirs(directory, exist_ok=True)
    ext = _FORMAT_EXTENSIONS.get((report_format or "txt").strip().lower(), "txt")
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(report_text)
    return path
