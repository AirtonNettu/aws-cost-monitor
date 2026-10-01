"""Testes dos formatos de relatório (JSON e Markdown) e do seletor."""

import json

from src.analysis.cost_analyzer import analyze_costs, compare_periods
from src.analysis.finops_rules import generate_alerts
from src.reports.report_generator import (
    build_report,
    build_report_for_format,
    build_report_json,
    build_report_markdown,
    save_report,
)


def test_json_estrutura_basica(costs_single_period):
    analysis = analyze_costs(costs_single_period)
    alerts = generate_alerts(analysis, None)
    raw = build_report_json(costs_single_period, analysis, None, alerts=alerts)
    data = json.loads(raw)
    assert data["total_cost"] == 50.0
    assert data["has_positive_cost"] is True
    assert data["largest_service"] == "Amazon EC2"
    assert data["services"]["Amazon EC2"] == 30.0
    assert isinstance(data["alerts"], list)
    assert data["comparison"] is None


def test_json_inclui_comparacao(costs_two_periods):
    analysis = analyze_costs(costs_two_periods)
    comparison = compare_periods(costs_two_periods)
    data = json.loads(build_report_json(costs_two_periods, analysis, comparison))
    assert data["comparison"]["previous_total"] == 100.0
    assert data["comparison"]["current_total"] == 150.0
    assert data["comparison"]["variation"] == 50.0


def test_json_variacao_none_quando_anterior_zero(costs_previous_zero):
    analysis = analyze_costs(costs_previous_zero)
    comparison = compare_periods(costs_previous_zero)
    data = json.loads(build_report_json(costs_previous_zero, analysis, comparison))
    assert data["comparison"]["variation"] is None


def test_json_sem_custo_positivo(costs_empty):
    analysis = analyze_costs(costs_empty)
    data = json.loads(build_report_json(costs_empty, analysis, None))
    assert data["has_positive_cost"] is False
    assert data["services"] == {}
    assert data["largest_service"] is None


def test_markdown_contem_secoes(costs_single_period):
    analysis = analyze_costs(costs_single_period)
    md = build_report_markdown(costs_single_period, analysis, None)
    assert "# AWS Cost Monitor" in md
    assert "## Custo por serviço" in md
    assert "## Alertas de FinOps" in md
    assert "## Interpretação da IA" in md
    assert "| Serviço | Custo (USD) | Participação |" in md


def test_markdown_sem_custo_positivo(costs_empty):
    analysis = analyze_costs(costs_empty)
    md = build_report_markdown(costs_empty, analysis, None)
    assert "Nenhum serviço apresentou custo positivo" in md


def test_seletor_json(costs_single_period):
    analysis = analyze_costs(costs_single_period)
    texto, fmt = build_report_for_format("json", costs_single_period, analysis, None)
    assert fmt == "json"
    json.loads(texto)  # deve ser JSON válido


def test_seletor_markdown_normaliza(costs_single_period):
    analysis = analyze_costs(costs_single_period)
    texto, fmt = build_report_for_format(
        "  MarkDown ", costs_single_period, analysis, None
    )
    assert fmt == "markdown"
    assert "# AWS Cost Monitor" in texto


def test_seletor_formato_desconhecido_cai_em_txt(costs_single_period):
    analysis = analyze_costs(costs_single_period)
    texto, fmt = build_report_for_format(
        "xml", costs_single_period, analysis, None
    )
    assert fmt == "txt"
    # Builder txt usa separadores de largura fixa.
    assert "AWS COST MONITOR" in texto


def test_seletor_default_txt(costs_single_period):
    analysis = analyze_costs(costs_single_period)
    texto, fmt = build_report_for_format(None, costs_single_period, analysis, None)
    assert fmt == "txt"
    assert texto == build_report(costs_single_period, analysis, None)


def test_save_report_extensao_por_formato(tmp_path):
    p_txt = save_report("conteudo", directory=str(tmp_path), report_format="txt")
    p_json = save_report("{}", directory=str(tmp_path), report_format="json")
    p_md = save_report("# md", directory=str(tmp_path), report_format="markdown")
    assert p_txt.endswith(".txt")
    assert p_json.endswith(".json")
    assert p_md.endswith(".md")
