"""Ponto de entrada do AWS Cost Monitor.

Orquestra o fluxo completo da V1:

    Cost Explorer -> análise determinística -> comparação -> IA -> relatório

Cada etapa trata seus erros de forma explícita, sem mascará-los. A ausência
da IA (Llama indisponível) não interrompe o fluxo: o relatório é gerado sem a
interpretação e o motivo é registrado no próprio relatório.
"""

import sys

from src import config
from src.ai.llama_client import LlamaUnavailableError, interpret
from src.analysis.cost_analyzer import analyze_costs, compare_periods
from src.aws.cost_explorer import CostExplorerError, get_costs
from src.reports.report_generator import build_report, save_report


def run():
    """Executa o fluxo completo e retorna o código de saída do processo."""
    # 1. Coleta ------------------------------------------------------------
    try:
        costs = get_costs()
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

    # 3. Interpretação por IA (opcional) ----------------------------------
    ai_interpretation = None
    ai_error = None
    if config.AI_ENABLED:
        try:
            ai_interpretation = interpret(analysis, comparison)
        except LlamaUnavailableError as error:
            ai_error = str(error)
            print(f"[AVISO] IA indisponível: {error}", file=sys.stderr)
    else:
        ai_error = "Camada de IA desativada por configuração (AI_ENABLED=false)."

    # 4. Relatório ---------------------------------------------------------
    report = build_report(
        costs=costs,
        analysis=analysis,
        comparison=comparison,
        ai_interpretation=ai_interpretation,
        ai_error=ai_error,
    )
    print(report)

    path = save_report(report)
    print(f"\nRelatório salvo em: {path}")
    return 0


def main():
    sys.exit(run())


if __name__ == "__main__":
    main()
