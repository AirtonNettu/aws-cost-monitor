"""Ponto de entrada do AWS Cost Monitor.

Orquestra o fluxo completo da V1:

    Cost Explorer -> análise determinística -> comparação -> IA -> relatório

Cada etapa trata seus erros de forma explícita, sem mascará-los. A ausência
da IA (Llama indisponível) não interrompe o fluxo: o relatório é gerado sem a
interpretação e o motivo é registrado no próprio relatório.
"""

import argparse
import os
import subprocess
import sys

from src import config
from src.ai.llama_client import LlamaUnavailableError, interpret
from src.analysis.cost_analyzer import analyze_costs, compare_periods
from src.analysis.finops_rules import generate_alerts
from src.aws.cost_explorer import CostExplorerError, get_costs
from src.database.repository import save_run
from src.reports.report_generator import build_report_for_format, save_report


def parse_args(args=None):
    """Configura e processa argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="AWS Cost Monitor — Ferramenta de FinOps com IA"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help=f"Janela de análise em dias (default: {config.COST_PERIOD_DAYS})",
    )
    parser.add_argument(
        "--granularity",
        choices=["DAILY", "MONTHLY"],
        default=None,
        help=f"Granularidade da consulta AWS (default: {config.COST_GRANULARITY})",
    )
    parser.add_argument(
        "--format",
        choices=["txt", "json", "markdown", "html"],
        default=None,
        help=f"Formato de saída do relatório (default: {config.REPORT_FORMAT})",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default=None,
        help="Chave de Cost Allocation Tag da AWS para agrupamento (ex: Environment, Project)",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help="Desativa a interpretação por IA nesta execução",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Inicializa o dashboard web interativo (Streamlit)",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Desativa a persistência automática no banco SQLite local",
    )
    return parser.parse_args(args)


def run(
    period_days=None,
    granularity=None,
    report_format=None,
    tag_key=None,
    ai_enabled=None,
    persist_db=True,
):
    """Executa o fluxo completo e retorna o código de saída do processo."""
    period_days = period_days or config.COST_PERIOD_DAYS
    granularity = granularity or config.COST_GRANULARITY
    report_format = report_format or config.REPORT_FORMAT
    tag_key = tag_key or config.COST_TAG_KEY
    ai_enabled = config.AI_ENABLED if ai_enabled is None else ai_enabled

    # 1. Coleta ------------------------------------------------------------
    try:
        costs = get_costs(
            period_days=period_days,
            granularity=granularity,
            tag_key=tag_key,
        )
    except CostExplorerError as error:
        print(f"[ERRO] Falha ao coletar custos: {error}", file=sys.stderr)
        return 1

    if not costs:
        print(
            "[AVISO] O Cost Explorer não retornou dados para o período. "
            "Verifique a janela de datas e se a conta possui custos registrados."
        )
        return 0

    # 2. Análise determinística -------------------------------------------
    analysis = analyze_costs(costs)
    comparison = compare_periods(costs)

    # 3. Regras determinísticas de FinOps ---------------------------------
    alerts = generate_alerts(analysis, comparison)

    # 4. Interpretação por IA (opcional) ----------------------------------
    ai_interpretation = None
    ai_error = None
    if ai_enabled:
        try:
            ai_interpretation = interpret(analysis, comparison, alerts)
        except LlamaUnavailableError as error:
            ai_error = str(error)
            print(f"[AVISO] IA indisponível: {error}", file=sys.stderr)
    else:
        ai_error = "Camada de IA desativada por configuração ou flag (--no-ai)."

    # 5. Relatório ---------------------------------------------------------
    report, fmt = build_report_for_format(
        report_format,
        costs=costs,
        analysis=analysis,
        comparison=comparison,
        ai_interpretation=ai_interpretation,
        ai_error=ai_error,
        alerts=alerts,
    )
    print(report)

    path = save_report(report, report_format=fmt)
    print(f"\nRelatório salvo em: {path}")

    # 6. Persistência local (não-bloqueante) --------------------------------
    if persist_db:
        try:
            run_id = save_run(
                costs=costs,
                analysis=analysis,
                comparison=comparison,
                ai_interpretation=ai_interpretation,
                alerts=alerts,
            )
            print(f"Snapshot gravado no banco de dados local (Run ID #{run_id}).")
        except Exception as exc:
            print(f"[AVISO] Falha ao persistir no SQLite: {exc}", file=sys.stderr)

    return 0


def main(args=None):
    parsed = parse_args(args)

    if parsed.dashboard:
        app_path = os.path.join(os.path.dirname(__file__), "dashboard", "app.py")
        cmd = [sys.executable, "-m", "streamlit", "run", app_path]
        sys.exit(subprocess.call(cmd))

    sys.exit(
        run(
            period_days=parsed.days,
            granularity=parsed.granularity,
            report_format=parsed.format,
            tag_key=parsed.tag,
            ai_enabled=False if parsed.no_ai else None,
            persist_db=not parsed.no_db,
        )
    )


if __name__ == "__main__":
    main()
