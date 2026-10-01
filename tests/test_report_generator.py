"""Testes da geração de relatório (sem IO de rede)."""

from src.analysis.cost_analyzer import analyze_costs, compare_periods
from src.reports.report_generator import build_report


def test_relatorio_com_custo_positivo(costs_single_period):
    analysis = analyze_costs(costs_single_period)
    report = build_report(costs_single_period, analysis, None)
    assert "Custo total: 50.00 USD" in report
    assert "Amazon EC2" in report
    assert "Maior serviço: Amazon EC2" in report


def test_relatorio_sem_custo_positivo(costs_empty):
    analysis = analyze_costs(costs_empty)
    report = build_report(costs_empty, analysis, None)
    assert "Nenhum serviço apresentou custo positivo" in report


def test_relatorio_inclui_interpretacao_da_ia(costs_single_period):
    analysis = analyze_costs(costs_single_period)
    report = build_report(
        costs_single_period, analysis, None, ai_interpretation="Texto da IA aqui."
    )
    assert "Texto da IA aqui." in report


def test_relatorio_registra_ia_indisponivel(costs_single_period):
    analysis = analyze_costs(costs_single_period)
    report = build_report(
        costs_single_period, analysis, None, ai_error="Llama fora do ar."
    )
    assert "Indisponível" in report
    assert "Llama fora do ar." in report


def test_relatorio_comparacao_zero_anterior(costs_previous_zero):
    analysis = analyze_costs(costs_previous_zero)
    comparison = compare_periods(costs_previous_zero)
    report = build_report(costs_previous_zero, analysis, comparison)
    assert "indisponível (período anterior com custo zero)" in report
