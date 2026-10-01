"""Testes da lógica determinística de análise de custos."""

import pytest

from src.analysis.cost_analyzer import analyze_costs, compare_periods


def test_total_cost(costs_single_period):
    result = analyze_costs(costs_single_period)
    assert result["total_cost"] == pytest.approx(50.0)


def test_agrupamento_por_servico(costs_single_period):
    result = analyze_costs(costs_single_period)
    assert result["services"] == {
        "Amazon S3": 10.0,
        "Amazon EC2": 30.0,
        "AWS Lambda": 10.0,
    }


def test_agrupamento_acumula_entre_periodos(costs_two_periods):
    # Amazon S3 aparece em dois períodos (100 + 150).
    result = analyze_costs(costs_two_periods)
    assert result["services"]["Amazon S3"] == pytest.approx(250.0)


def test_percentual_por_servico(costs_single_period):
    result = analyze_costs(costs_single_period)
    assert result["percentages"]["Amazon EC2"] == pytest.approx(60.0)
    assert result["percentages"]["Amazon S3"] == pytest.approx(20.0)
    assert sum(result["percentages"].values()) == pytest.approx(100.0)


def test_maior_servico(costs_single_period):
    result = analyze_costs(costs_single_period)
    assert result["largest_service"] == "Amazon EC2"


def test_dados_vazios(costs_empty):
    result = analyze_costs(costs_empty)
    assert result["total_cost"] == 0.0
    assert result["positive_services"] == {}
    assert result["percentages"] == {}
    assert result["largest_service"] is None
    assert result["has_positive_cost"] is False


def test_valor_negativo_nao_entra_em_positivos(costs_with_negative):
    result = analyze_costs(costs_with_negative)
    # Total = 40 - 10 = 30; apenas EC2 é positivo.
    assert result["total_cost"] == pytest.approx(30.0)
    assert "Refund" not in result["positive_services"]
    assert result["largest_service"] == "Amazon EC2"


def test_comparacao_entre_periodos(costs_two_periods):
    result = compare_periods(costs_two_periods)
    assert result["previous_total"] == pytest.approx(100.0)
    assert result["current_total"] == pytest.approx(150.0)
    assert result["variation"] == pytest.approx(50.0)


def test_comparacao_periodo_anterior_zero(costs_previous_zero):
    result = compare_periods(costs_previous_zero)
    # Divisão por zero evitada: variação deve ser None.
    assert result["previous_total"] == 0.0
    assert result["variation"] is None


def test_comparacao_periodos_insuficientes(costs_single_period):
    assert compare_periods(costs_single_period) is None
