"""Read-only API contract and integration tests; no real AWS or Ollama requests."""

import pytest
from fastapi.testclient import TestClient

from src import config
from src.api.app import app
from src.database.repository import init_db, save_run
from src.database.seeds import seed_fixtures

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Garante que cada teste da API use um banco de dados SQLite isolado."""
    db_file = str(tmp_path / "api_test.db")
    monkeypatch.setattr(config, "DATABASE_PATH", db_file)
    init_db(db_file)
    return db_file


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_latest_snapshot_not_found_returns_404():
    response = client.get("/api/v1/snapshots/latest?days=30")
    assert response.status_code == 404
    assert "Nenhum snapshot encontrado" in response.json()["detail"]


def test_invalid_days_rejected_with_422():
    response = client.get("/api/v1/snapshots/latest?days=999")
    assert response.status_code == 422


def test_invalid_limit_rejected_with_422():
    response = client.get("/api/v1/runs?limit=0")
    assert response.status_code == 422

    response_high = client.get("/api/v1/runs?limit=101")
    assert response_high.status_code == 422


def test_latest_snapshot_and_runs_with_seeded_data(isolated_db):
    seed_fixtures(db_path=isolated_db)

    # 1. Busca snapshot padrão 30 dias
    res30 = client.get("/api/v1/snapshots/latest?days=30")
    assert res30.status_code == 200
    data30 = res30.json()
    assert data30["currency"] == "USD"
    assert data30["period"]["start"] < data30["period"]["end"]
    assert "T" in data30["collected_at"]
    assert data30["summary"]["total_cost"] > 0
    assert data30["summary"]["alert_count"] >= 0
    assert isinstance(data30["services"], list)
    assert isinstance(data30["timeline"], list)
    assert isinstance(data30["alerts"], list)
    assert data30["ai"]["status"] in {"ready", "processing", "unavailable"}
    assert 30 in data30["available_filters"]["days"]

    # 2. Busca snapshot 7 dias com tag
    res7 = client.get(
        "/api/v1/snapshots/latest?days=7&tag=Environment%3A+Production"
    )
    assert res7.status_code == 200
    data7 = res7.json()
    assert data7["tag"] == "Environment: Production"

    # 3. Tag inexistente retorna 404
    res_na = client.get("/api/v1/snapshots/latest?days=30&tag=TagInexistente")
    assert res_na.status_code == 404

    # 4. Listagem de execuções recentes
    res_runs = client.get("/api/v1/runs?limit=10")
    assert res_runs.status_code == 200
    runs_data = res_runs.json()
    assert "runs" in runs_data
    assert len(runs_data["runs"]) > 0
    first_run = runs_data["runs"][0]
    assert "id" in first_run
    assert "collected_at" in first_run
    assert "period" in first_run
    assert "total_cost" in first_run

    # 5. Busca execução por ID
    run_id = first_run["id"]
    res_by_id = client.get(f"/api/v1/runs/{run_id}")
    assert res_by_id.status_code == 200
    assert res_by_id.json()["id"] == run_id


def test_get_run_not_found():
    response = client.get("/api/v1/runs/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Snapshot nao encontrado."

    # ID alfanumérico não-numérico também retorna 404 seguro
    response_alpha = client.get("/api/v1/runs/nao-existe")
    assert response_alpha.status_code == 404


def test_legacy_snapshot_naive_timezone_conflict(isolated_db):
    """Execuções legadas gravadas com datetime ingênuo (sem UTC) retornam 409 em vez de

    falsificar fuso horário no contrato.
    """
    import sqlite3
    conn = sqlite3.connect(isolated_db)
    conn.execute("""
        INSERT INTO runs (
            created_at, period_start, period_end, total_cost,
            has_positive_cost, largest_service, alerts_json
        ) VALUES (
            '2026-09-01T10:00:00', '2026-08-01', '2026-09-01', 50.0,
            1, 'Amazon EC2', '[]'
        )
    """)
    conn.commit()
    conn.close()

    res = client.get("/api/v1/runs/1")
    assert res.status_code == 409
    assert "Snapshot legado sem fuso horario" in res.json()["detail"]


def test_download_report_formats(isolated_db):
    seed_fixtures(db_path=isolated_db)
    res_runs = client.get("/api/v1/runs?limit=1")
    run_id = res_runs.json()["runs"][0]["id"]

    for fmt in ["json", "markdown", "html", "txt"]:
        res = client.get(f"/api/v1/runs/{run_id}/reports/{fmt}")
        assert res.status_code == 200
        assert f"report-run-{run_id}" in res.headers["content-disposition"]
        assert len(res.content) > 0

    # Formato não suportado retorna 404
    res_unsupported = client.get(f"/api/v1/runs/{run_id}/reports/exe")
    assert res_unsupported.status_code == 404

    # Run inexistente retorna 404
    res_404 = client.get("/api/v1/runs/999999/reports/json")
    assert res_404.status_code == 404


def test_cors_preflight_and_headers():
    response = client.options(
        "/api/v1/snapshots/latest",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
