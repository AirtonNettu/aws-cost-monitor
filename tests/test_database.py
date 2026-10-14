"""Testes para o repositório SQLite de persistência de custos."""

import pytest

from src.analysis.cost_analyzer import analyze_costs, compare_periods
from src.analysis.finops_rules import generate_alerts
from src.database.repository import (
    get_history,
    get_latest_run,
    get_run_services,
    init_db,
    save_run,
)


@pytest.fixture
def temp_db(tmp_path):
    return str(tmp_path / "test_costs.db")


def test_init_db(temp_db):
    init_db(temp_db)
    # Segunda inicialização idempotente
    init_db(temp_db)
    latest = get_latest_run(temp_db)
    assert latest is None


def test_save_run_and_get_history(costs_single_period, temp_db):
    analysis = analyze_costs(costs_single_period)
    alerts = generate_alerts(analysis, None)
    run_id = save_run(
        costs=costs_single_period,
        analysis=analysis,
        comparison=None,
        ai_interpretation="IA ok",
        alerts=alerts,
        db_path=temp_db,
    )
    assert run_id > 0

    history = get_history(limit=10, db_path=temp_db)
    assert len(history) == 1
    assert history[0]["total_cost"] == 50.0
    assert history[0]["largest_service"] == "Amazon EC2"
    assert history[0]["ai_interpretation"] == "IA ok"
    assert isinstance(history[0]["alerts"], list)

    services = get_run_services(run_id, db_path=temp_db)
    assert len(services) == 3
    assert services[0]["service_name"] == "Amazon EC2"
    assert services[0]["amount"] == 30.0


def test_get_latest_run(costs_two_periods, temp_db):
    analysis = analyze_costs(costs_two_periods)
    comparison = compare_periods(costs_two_periods)
    save_run(
        costs=costs_two_periods,
        analysis=analysis,
        comparison=comparison,
        ai_interpretation=None,
        alerts=[],
        db_path=temp_db,
    )

    latest = get_latest_run(temp_db)
    assert latest is not None
    assert latest["total_cost"] == 250.0
    assert latest["previous_total"] == 100.0
    assert latest["variation"] == 50.0
    assert len(latest["services"]) == 1
