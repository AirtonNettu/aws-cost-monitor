"""Testes das regras determinísticas de FinOps."""

from src import config
from src.analysis.cost_analyzer import analyze_costs, compare_periods
from src.analysis.finops_rules import generate_alerts


def _alert_types(alerts):
    return {alert["type"] for alert in alerts}


def test_sem_custo_positivo_nao_gera_alertas(costs_empty):
    analysis = analyze_costs(costs_empty)
    comparison = compare_periods(costs_empty)
    alerts = generate_alerts(analysis, comparison)
    assert alerts == []


def test_concentracao_gera_alerta(costs_single_period):
    # EC2 = 30 de 50 = 60%, acima do limiar default (50%).
    analysis = analyze_costs(costs_single_period)
    alerts = generate_alerts(analysis, None)
    assert "concentration" in _alert_types(alerts)
    concentracao = next(a for a in alerts if a["type"] == "concentration")
    assert "Amazon EC2" in concentracao["message"]
    assert concentracao["severity"] == "warning"


def test_top_services_sempre_presente_com_custo_positivo(costs_single_period):
    analysis = analyze_costs(costs_single_period)
    alerts = generate_alerts(analysis, None)
    assert "top_services" in _alert_types(alerts)
    top = next(a for a in alerts if a["type"] == "top_services")
    assert "Amazon EC2" in top["message"]
    assert top["severity"] == "info"


def test_crescimento_acima_do_limiar_gera_alerta(costs_two_periods):
    # 100 -> 150 = +50%, acima do limiar default (20%).
    analysis = analyze_costs(costs_two_periods)
    comparison = compare_periods(costs_two_periods)
    alerts = generate_alerts(analysis, comparison)
    assert "growth" in _alert_types(alerts)
    growth = next(a for a in alerts if a["type"] == "growth")
    assert "50.0%" in growth["message"]


def test_crescimento_abaixo_do_limiar_nao_gera_alerta(monkeypatch, costs_two_periods):
    # Eleva o limiar acima da variação (50%) para não disparar.
    monkeypatch.setattr(config, "FINOPS_GROWTH_THRESHOLD", 80.0)
    analysis = analyze_costs(costs_two_periods)
    comparison = compare_periods(costs_two_periods)
    alerts = generate_alerts(analysis, comparison)
    assert "growth" not in _alert_types(alerts)


def test_crescimento_sem_comparacao_nao_quebra(costs_single_period):
    analysis = analyze_costs(costs_single_period)
    alerts = generate_alerts(analysis, None)
    assert "growth" not in _alert_types(alerts)


def test_variacao_none_nao_gera_crescimento(costs_previous_zero):
    # Período anterior zero -> variation None -> sem alerta de crescimento.
    analysis = analyze_costs(costs_previous_zero)
    comparison = compare_periods(costs_previous_zero)
    alerts = generate_alerts(analysis, comparison)
    assert "growth" not in _alert_types(alerts)


def test_top_n_respeita_configuracao(monkeypatch, costs_single_period):
    monkeypatch.setattr(config, "FINOPS_TOP_N", 1)
    analysis = analyze_costs(costs_single_period)
    alerts = generate_alerts(analysis, None)
    top = next(a for a in alerts if a["type"] == "top_services")
    # Apenas o maior serviço (EC2) deve aparecer; S3/Lambda não.
    assert "Amazon EC2" in top["message"]
    assert "AWS Lambda" not in top["message"]
