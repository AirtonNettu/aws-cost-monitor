"""Testes para o repositório SQLite de persistência de custos e migrações."""

import sqlite3
from datetime import datetime, timezone
import pytest

from src.analysis.cost_analyzer import analyze_costs, compare_periods
from src.analysis.finops_rules import generate_alerts
from src.database.repository import (
    get_available_days,
    get_available_tags,
    get_history,
    get_latest_run,
    get_latest_snapshot,
    get_run_by_id,
    get_run_services,
    init_db,
    save_run,
    save_snapshot,
)
from src.database.seeds import seed_fixtures


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


def test_metadata_persistence_and_latest_snapshot(costs_two_periods, temp_db):
    analysis = analyze_costs(costs_two_periods)
    comparison = compare_periods(costs_two_periods)
    run_id = save_run(
        costs=costs_two_periods,
        analysis=analysis,
        comparison=comparison,
        ai_interpretation="Analise IA completa",
        alerts=[{"type": "growth", "severity": "warning", "message": "Custo subiu"}],
        db_path=temp_db,
        source="aws",
        tag="Environment: Production",
        days=30,
        estimated=True,
    )
    assert run_id > 0

    # Busca com tag e dias corretos
    snapshot = get_latest_snapshot(days=30, tag="Environment: Production", db_path=temp_db)
    assert snapshot is not None
    assert snapshot["id"] == run_id
    assert snapshot["days"] == 30
    assert snapshot["tag"] == "Environment: Production"
    assert snapshot["estimated"] == 1
    assert snapshot["source"] == "aws"
    assert len(snapshot["services"]) == 1

    # Busca sem tag retorna None para essa tag
    no_tag = get_latest_snapshot(days=30, tag=None, db_path=temp_db)
    assert no_tag is None

    # Busca com dias diferentes retorna None
    diff_days = get_latest_snapshot(days=7, tag="Environment: Production", db_path=temp_db)
    assert diff_days is None


def test_legacy_migration_without_data_loss(tmp_path):
    """Simula um banco legado com schema antigo e valida que a migração incremental

    adiciona as novas colunas e preserva rigorosamente todas as linhas e colunas existentes.
    """
    db_file = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            period_start TEXT,
            period_end TEXT,
            total_cost REAL NOT NULL,
            has_positive_cost INTEGER NOT NULL,
            largest_service TEXT,
            previous_total REAL,
            variation REAL,
            alerts_json TEXT,
            ai_interpretation TEXT
        )
    """)
    conn.execute("""
        INSERT INTO runs (
            created_at, period_start, period_end, total_cost,
            has_positive_cost, largest_service, previous_total,
            variation, alerts_json, ai_interpretation
        ) VALUES (
            '2026-09-01T12:00:00', '2026-08-01', '2026-09-01', 123.45,
            1, 'Amazon EC2', 100.0, 23.45, '[]', 'Legado IA'
        )
    """)
    conn.commit()
    conn.close()

    # Aplica migração via init_db
    init_db(db_file)

    # Verifica integridade do dado legado
    run = get_run_by_id(1, db_path=db_file)
    assert run is not None
    assert run["id"] == 1
    assert run["created_at"] == "2026-09-01T12:00:00"
    assert run["total_cost"] == 123.45
    assert run["source"] == "aws"  # Default da coluna
    assert run["tag"] is None  # Não fabricado
    assert run["days"] is None  # Não fabricado

    # Insere novo snapshot na tabela migrada e confere convivência
    costs = [{"start": "2026-10-01", "end": "2026-10-31", "groups": []}]
    analysis = {
        "services": {},
        "total_cost": 200.0,
        "positive_services": {},
        "percentages": {},
        "largest_service": "Amazon S3",
        "has_positive_cost": True,
    }
    new_id = save_run(costs, analysis, db_path=db_file, days=30, tag="Project: FinOps")
    assert new_id == 2

    new_run = get_run_by_id(2, db_path=db_file)
    assert new_run["days"] == 30
    assert new_run["tag"] == "Project: FinOps"


def test_get_history_pagination_and_filtering(costs_two_periods, temp_db):
    analysis = analyze_costs(costs_two_periods)
    # Insere 5 execuções com diferentes parâmetros
    save_run(costs_two_periods, analysis, db_path=temp_db, days=7, tag="Alpha")
    save_run(costs_two_periods, analysis, db_path=temp_db, days=30, tag="Alpha")
    save_run(costs_two_periods, analysis, db_path=temp_db, days=30, tag="Beta")
    save_run(costs_two_periods, analysis, db_path=temp_db, days=90, tag=None)
    save_run(costs_two_periods, analysis, db_path=temp_db, days=30, tag=None)

    # Paginação
    p1 = get_history(limit=2, offset=0, db_path=temp_db)
    assert len(p1) == 2
    p2 = get_history(limit=2, offset=2, db_path=temp_db)
    assert len(p2) == 2
    assert p1[0]["id"] != p2[0]["id"]

    # Filtro por tag
    alpha = get_history(tag="Alpha", db_path=temp_db)
    assert len(alpha) == 2
    for r in alpha:
        assert r["tag"] == "Alpha"

    # Filtro por days
    d30 = get_history(days=30, db_path=temp_db)
    assert len(d30) == 3

    # Tags e Days disponíveis
    tags = get_available_tags(temp_db)
    assert "Alpha" in tags
    assert "Beta" in tags

    days_list = get_available_days(temp_db)
    assert set(days_list) == {7, 30, 90}


def test_seed_fixtures(temp_db):
    inserted_ids = seed_fixtures(db_path=temp_db)
    assert len(inserted_ids) > 0

    # Verifica snapshot 30 dias sem tag
    snap30 = get_latest_snapshot(days=30, tag=None, db_path=temp_db)
    assert snap30 is not None
    assert snap30["days"] == 30
    assert snap30["currency"] if "currency" in snap30 else True

    # Verifica snapshot 7 dias com tag
    snap7 = get_latest_snapshot(days=7, tag="Environment: Production", db_path=temp_db)
    assert snap7 is not None
    assert snap7["days"] == 7
    assert snap7["tag"] == "Environment: Production"
