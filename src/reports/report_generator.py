"""Geração do relatório final de custos.

Responsabilidade única: transformar os dados já calculados (analyzer) e a
interpretação da IA (quando disponível) em um relatório legível. Não calcula
valores nem chama a AWS/IA diretamente.
"""

import html
import json
import os
from datetime import datetime

from src import config

# Extensão de arquivo por formato de relatório.
_FORMAT_EXTENSIONS = {"txt": "txt", "json": "json", "markdown": "md", "html": "html"}


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


def build_report_html(
    costs,
    analysis,
    comparison,
    ai_interpretation=None,
    ai_error=None,
    alerts=None,
):
    """Monta o relatório como página HTML standalone e interativa."""
    period_str = html.escape(_format_period(costs))
    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_cost_str = _money(analysis["total_cost"])

    # Ordena serviços positivos
    sorted_services = sorted(
        analysis["positive_services"].items(),
        key=lambda item: item[1],
        reverse=True,
    ) if analysis["has_positive_cost"] else []

    # Dados para o gráfico Chart.js
    chart_labels = [s[0] for s in sorted_services]
    chart_values = [round(float(s[1]), 2) for s in sorted_services]

    # Prepara variação
    if comparison is None:
        var_badge = '<span class="badge badge-neutral">Sem histórico</span>'
        var_detail = "Período único analisado"
    elif comparison["variation"] is not None:
        var_val = comparison["variation"]
        if var_val > 0:
            var_badge = f'<span class="badge badge-danger">+{var_val:.1f}%</span>'
        elif var_val < 0:
            var_badge = f'<span class="badge badge-success">{var_val:.1f}%</span>'
        else:
            var_badge = '<span class="badge badge-neutral">0.0%</span>'
        var_detail = f"Anterior: ${_money(comparison['previous_total'])} USD"
    else:
        var_badge = '<span class="badge badge-neutral">Indisponível</span>'
        var_detail = "Período anterior com custo zero"

    # Maior serviço
    largest_srv = html.escape(analysis["largest_service"]) if analysis["largest_service"] else "Nenhum"
    largest_pct = analysis["percentages"].get(analysis["largest_service"], 0.0) if analysis["largest_service"] else 0.0

    # Linhas da tabela de serviços
    table_rows = []
    if sorted_services:
        for srv, amt in sorted_services:
            pct = analysis["percentages"].get(srv, 0.0)
            srv_escaped = html.escape(srv)
            table_rows.append(f"""
                <tr>
                    <td class="font-medium text-slate-800">{srv_escaped}</td>
                    <td class="text-right font-mono font-semibold">${_money(amt)} USD</td>
                    <td class="text-right">
                        <div class="flex items-center justify-end gap-2">
                            <span class="text-xs font-mono text-slate-500">{pct:.1f}%</span>
                            <div class="w-16 bg-slate-100 rounded-full h-2 overflow-hidden">
                                <div class="bg-indigo-600 h-2 rounded-full" style="width: {min(pct, 100):.1f}%"></div>
                            </div>
                        </div>
                    </td>
                </tr>
            """)
    else:
        table_rows.append('<tr><td colspan="3" class="text-center py-4 text-slate-400">Nenhum serviço com custo positivo no período.</td></tr>')

    table_rows_html = "".join(table_rows)

    # Alertas de FinOps
    alerts_html_items = []
    if alerts:
        for al in alerts:
            sev = al["severity"].lower()
            msg = html.escape(al["message"])
            if sev == "warning":
                badge_class = "alert-warning"
                icon = "⚠️"
            elif sev == "info":
                badge_class = "alert-info"
                icon = "ℹ️"
            else:
                badge_class = "alert-danger"
                icon = "🚨"
            alerts_html_items.append(f"""
                <div class="alert-card {badge_class}">
                    <span class="text-lg">{icon}</span>
                    <div>
                        <strong class="uppercase text-xs tracking-wider">{sev}</strong>
                        <p class="text-sm mt-0.5">{msg}</p>
                    </div>
                </div>
            """)
    else:
        alerts_html_items.append("""
            <div class="alert-card alert-success">
                <span class="text-lg">✅</span>
                <div>
                    <strong class="uppercase text-xs tracking-wider">OK</strong>
                    <p class="text-sm mt-0.5">Nenhum alerta ou anomalia detectada pelas regras de FinOps.</p>
                </div>
            </div>
        """)
    alerts_section_html = "".join(alerts_html_items)

    # Bloco da IA
    if ai_interpretation:
        ai_box_html = f"""
            <div class="ai-box">
                <div class="ai-header">
                    <span class="text-xl">🤖</span>
                    <h3 class="text-base font-semibold text-slate-800">Parecer Executivo FinOps (IA)</h3>
                </div>
                <div class="ai-content">
                    {html.escape(ai_interpretation).replace(chr(10), '<br>')}
                </div>
            </div>
        """
    elif ai_error:
        ai_box_html = f"""
            <div class="ai-box ai-box-unavailable">
                <div class="ai-header">
                    <span class="text-xl">⚠️</span>
                    <h3 class="text-base font-semibold text-amber-800">Interpretação da IA Indisponível</h3>
                </div>
                <p class="text-sm text-amber-700 mt-2">{html.escape(ai_error)}</p>
            </div>
        """
    else:
        ai_box_html = """
            <div class="ai-box ai-box-neutral">
                <p class="text-sm text-slate-500">Interpretação por IA não solicitada para esta execução.</p>
            </div>
        """

    # HTML completo
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Cost Monitor — Relatório de Custos</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8fafc;
            color: #1e293b;
            line-height: 1.5;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}
        .header {{
            background: #ffffff;
            border-radius: 12px;
            padding: 1.5rem 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
            border-left: 6px solid #4f46e5;
        }}
        .header h1 {{
            font-size: 1.4rem;
            font-weight: 700;
            color: #0f172a;
        }}
        .header p {{
            font-size: 0.85rem;
            color: #64748b;
        }}
        .grid-kpis {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .kpi-card {{
            background: #ffffff;
            border-radius: 12px;
            padding: 1.25rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border: 1px solid #e2e8f0;
        }}
        .kpi-title {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            margin-bottom: 0.5rem;
        }}
        .kpi-value {{
            font-size: 1.6rem;
            font-weight: 700;
            color: #0f172a;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }}
        .kpi-footer {{
            margin-top: 0.5rem;
            font-size: 0.8rem;
            color: #64748b;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-danger {{ background: #fee2e2; color: #991b1b; }}
        .badge-success {{ background: #dcfce7; color: #166534; }}
        .badge-neutral {{ background: #f1f5f9; color: #475569; }}

        .grid-main {{
            display: grid;
            grid-template-columns: 3fr 2fr;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        @media (max-width: 850px) {{
            .grid-main {{ grid-template-columns: 1fr; }}
        }}
        .card {{
            background: #ffffff;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            border: 1px solid #e2e8f0;
        }}
        .card-title {{
            font-size: 1rem;
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
        }}
        th {{
            text-align: left;
            padding: 0.6rem 0.75rem;
            border-bottom: 1px solid #e2e8f0;
            color: #64748b;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
        }}
        td {{
            padding: 0.75rem;
            border-bottom: 1px solid #f1f5f9;
        }}
        tr:hover td {{ background: #f8fafc; }}

        .alert-card {{
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 0.75rem;
            border: 1px solid transparent;
        }}
        .alert-warning {{ background: #fffbeb; border-color: #fde68a; color: #92400e; }}
        .alert-info {{ background: #eff6ff; border-color: #bfdbfe; color: #1e40af; }}
        .alert-danger {{ background: #fef2f2; border-color: #fecaca; color: #991b1b; }}
        .alert-success {{ background: #f0fdf4; border-color: #bbf7d0; color: #166534; }}

        .ai-box {{
            background: #ffffff;
            border: 1px solid #e0e7ff;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 2px 4px rgba(79, 70, 229, 0.05);
            background: linear-gradient(180deg, #ffffff 0%, #faf5ff 100%);
        }}
        .ai-box-unavailable {{ background: #fffbeb; border-color: #fde68a; }}
        .ai-box-neutral {{ background: #f8fafc; border-color: #e2e8f0; }}
        .ai-header {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.75rem;
        }}
        .ai-content {{
            font-size: 0.95rem;
            line-height: 1.6;
            color: #334155;
            white-space: pre-line;
        }}

        .footer {{
            text-align: center;
            font-size: 0.75rem;
            color: #94a3b8;
            margin-top: 2rem;
        }}
        .chart-container {{
            position: relative;
            max-width: 280px;
            margin: 0 auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Cabeçalho -->
        <header class="header">
            <div>
                <h1>AWS Cost Monitor — Relatório de Custos</h1>
                <p>Período: <strong>{period_str}</strong></p>
            </div>
            <div style="text-align: right;">
                <p>Gerado em: <strong>{gen_time}</strong></p>
                <p>Modo: <span class="badge badge-neutral">FinOps Determinístico</span></p>
            </div>
        </header>

        <!-- KPIs -->
        <div class="grid-kpis">
            <div class="kpi-card">
                <div class="kpi-title">Custo Total</div>
                <div class="kpi-value">${total_cost_str}</div>
                <div class="kpi-footer">Moeda: USD</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Variação vs. Anterior</div>
                <div class="kpi-value">{var_badge}</div>
                <div class="kpi-footer">{var_detail}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Maior Serviço</div>
                <div class="kpi-value" style="font-size: 1.2rem; font-family: inherit;">{largest_srv}</div>
                <div class="kpi-footer">Representa {largest_pct:.1f}% do total</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Alertas FinOps</div>
                <div class="kpi-value">{len(alerts) if alerts else 0}</div>
                <div class="kpi-footer">Heurísticas avaliadas</div>
            </div>
        </div>

        <!-- Parecer de IA -->
        {ai_box_html}

        <!-- Seção Principal: Tabela e Gráfico -->
        <div class="grid-main">
            <div class="card">
                <div class="card-title">
                    <span>Detalhamento por Serviço</span>
                    <span style="font-size: 0.8rem; color: #64748b;">{len(sorted_services)} ativos</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Serviço</th>
                            <th style="text-align: right;">Custo</th>
                            <th style="text-align: right;">Participação</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html}
                    </tbody>
                </table>
            </div>

            <div class="card">
                <div class="card-title">Distribuição de Gastos</div>
                <div class="chart-container">
                    <canvas id="costChart"></canvas>
                </div>
            </div>
        </div>

        <!-- Alertas de FinOps -->
        <div class="card" style="margin-bottom: 1.5rem;">
            <div class="card-title">Regras e Alertas de FinOps</div>
            {alerts_section_html}
        </div>

        <footer class="footer">
            <p>AWS Cost Monitor &bull; FinOps com Python e IA Desacoplada &bull; MIT License</p>
        </footer>
    </div>

    <script>
        const labels = {json.dumps(chart_labels, ensure_ascii=False)};
        const dataValues = {json.dumps(chart_values)};
        const colors = [
            '#4f46e5', '#06b6d4', '#10b981', '#f59e0b',
            '#ef4444', '#8b5cf6', '#ec4899', '#64748b'
        ];

        if (labels.length > 0 && typeof Chart !== 'undefined') {{
            const ctx = document.getElementById('costChart').getContext('2d');
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: labels,
                    datasets: [{{
                        data: dataValues,
                        backgroundColor: colors.slice(0, labels.length),
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{ boxWidth: 12, font: {{ size: 11 }} }}
                        }}
                    }}
                }}
            }});
        }}
    </script>
</body>
</html>"""


# Mapa formato normalizado -> função construtora.
_BUILDERS = {
    "txt": build_report,
    "json": build_report_json,
    "markdown": build_report_markdown,
    "html": build_report_html,
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
