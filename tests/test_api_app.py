"""Read-only API contract, integrity and regression tests; no real AWS or Ollama requests."""

import math
import sqlite3
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src import config
from src.api.app import Comparison, Period, RunSummary, ServiceCost, Summary, TimelinePoint, app
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


def test_list_runs_consistent_pagination_with_interspersed_legacy(isolated_db):
    """Testa que a listagem via API (/runs) possui paginação 100% consistente

    mesmo com a presença de registros legados incompatíveis no SQLite.
    """
    # 1. Insere registros legados incompatíveis
    conn = sqlite3.connect(isolated_db)
    for i in range(1, 4):
        conn.execute(
            """
            INSERT INTO runs (
                created_at, period_start, period_end, total_cost,
                has_positive_cost, largest_service, alerts_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"2026-08-0{i}T12:00:00",
                "2026-07-01",
                "2026-08-01",
                float(i * 10),
                1,
                "Amazon EC2",
                "[]",
            ),
        )
    conn.commit()
    conn.close()

    # 2. Insere 6 registros compatíveis
    for i in range(1, 7):
        save_run(
            costs=[{"start": f"2026-10-{i:02d}", "end": f"2026-10-{(i+1):02d}", "groups": []}],
            analysis={
                "services": {"Amazon EC2": float(i * 5)},
                "total_cost": float(i * 5),
                "positive_services": {"Amazon EC2": float(i * 5)},
                "percentages": {"Amazon EC2": 100.0},
                "largest_service": "Amazon EC2",
                "has_positive_cost": True,
            },
            days=30,
            db_path=isolated_db,
        )

    # Página 1 (limit=3, offset=0) deve retornar exatamente 3 registros
    res1 = client.get("/api/v1/runs?limit=3&offset=0")
    assert res1.status_code == 200
    runs1 = res1.json()["runs"]
    assert len(runs1) == 3

    # Página 2 (limit=3, offset=3) deve retornar os próximos 3 registros
    res2 = client.get("/api/v1/runs?limit=3&offset=3")
    assert res2.status_code == 200
    runs2 = res2.json()["runs"]
    assert len(runs2) == 3

    # Os conjuntos de IDs de páginas contíguas não podem se interceptar
    ids_page1 = {r["id"] for r in runs1}
    ids_page2 = {r["id"] for r in runs2}
    assert ids_page1.isdisjoint(ids_page2)
    assert len(ids_page1 | ids_page2) == 6


def test_pydantic_rejects_nan_and_infinity_and_preserves_negative_credits():
    """Valida a integridade estrita dos modelos Pydantic contra NaN e Infinity."""
    # 1. Summary rejeita NaN e Infinito
    with pytest.raises(ValidationError):
        Summary(total_cost=float("nan"), largest_service=None, largest_service_percentage=None, alert_count=0)

    with pytest.raises(ValidationError):
        Summary(total_cost=float("inf"), largest_service=None, largest_service_percentage=None, alert_count=0)

    # Aceita valores negativos legítimos (créditos / reembolsos)
    valid_summary = Summary(total_cost=-50.25, largest_service="Amazon S3", largest_service_percentage=100.0, alert_count=1)
    assert valid_summary.total_cost == -50.25

    # 2. ServiceCost rejeita NaN e aceita negativo
    with pytest.raises(ValidationError):
        ServiceCost(name="EC2", amount=float("nan"), percentage=50.0)

    credit_service = ServiceCost(name="Credit Refund", amount=-25.0, percentage=-10.0)
    assert credit_service.amount == -25.0

    # 3. TimelinePoint rejeita Infinity
    with pytest.raises(ValidationError):
        TimelinePoint(date="2026-10-01", amount=float("inf"))

    # 4. RunSummary rejeita NaN
    with pytest.raises(ValidationError):
        RunSummary(
            id="1",
            collected_at="2026-10-20T12:00:00Z",
            period=Period(start="2026-10-01", end="2026-10-20"),
            estimated=False,
            total_cost=float("nan"),
            largest_service=None,
        )


def test_comparison_period_equivalence_regression(isolated_db):
    """Testa que a equivalência de períodos é estritamente avaliada e refletida no snapshot."""
    # Cenário 1: Períodos contíguos de mesma duração (30 dias) e mesmo escopo -> equivalent_periods = True
    save_run(
        costs=[
            {"start": "2026-10-01", "end": "2026-10-31", "groups": []},
        ],
        analysis={
            "services": {"Amazon EC2": 100.0},
            "total_cost": 100.0,
            "positive_services": {"Amazon EC2": 100.0},
            "percentages": {"Amazon EC2": 100.0},
            "largest_service": "Amazon EC2",
            "has_positive_cost": True,
        },
        comparison={
            "previous_total": 80.0,
            "current_total": 100.0,
            "variation": 25.0,
            "previous_period": {"start": "2026-09-01", "end": "2026-10-01"},
        },
        days=30,
        tag="Env: Prod",
        db_path=isolated_db,
    )

    snap = client.get("/api/v1/snapshots/latest?days=30&tag=Env%3A+Prod").json()
    assert snap["comparison"]["equivalent_periods"] is True

    # Cenário 2: Períodos sobrepostos -> equivalent_periods = False
    save_run(
        costs=[
            {"start": "2026-10-01", "end": "2026-10-31", "groups": []},
        ],
        analysis={
            "services": {"Amazon EC2": 100.0},
            "total_cost": 100.0,
            "positive_services": {"Amazon EC2": 100.0},
            "percentages": {"Amazon EC2": 100.0},
            "largest_service": "Amazon EC2",
            "has_positive_cost": True,
        },
        comparison={
            "previous_total": 80.0,
            "current_total": 100.0,
            "variation": 25.0,
            "previous_period": {"start": "2026-10-15", "end": "2026-11-14"},  # Sobreposto com 2026-10-01 a 2026-10-31
        },
        days=30,
        tag="Env: Overlap",
        db_path=isolated_db,
    )

    snap_overlap = client.get("/api/v1/snapshots/latest?days=30&tag=Env%3A+Overlap").json()
    assert snap_overlap["comparison"]["equivalent_periods"] is False


def test_api_key_auth_enforcement(monkeypatch):
    """Garante que endpoints protegidos exigem X-API-Key quando API_KEY está configurada."""
    monkeypatch.setenv("API_KEY", "super-secret-finops-key")

    # 1. Health deve continuar público
    res_health = client.get("/api/v1/health")
    assert res_health.status_code == 200

    # 2. Endpoint protegido sem header retorna 401
    res_unauth = client.get("/api/v1/snapshots/latest?days=30")
    assert res_unauth.status_code == 401
    assert "Chave de API inválida" in res_unauth.json()["detail"]

    # 3. Endpoint protegido com chave errada retorna 401
    res_wrong = client.get(
        "/api/v1/snapshots/latest?days=30",
        headers={"X-API-Key": "wrong-key"},
    )
    assert res_wrong.status_code == 401

    # 4. Endpoint protegido com chave correta responde normalmente (ou 404 se sem dados)
    res_auth = client.get(
        "/api/v1/snapshots/latest?days=30",
        headers={"X-API-Key": "super-secret-finops-key"},
    )
    assert res_auth.status_code in (200, 404)


def test_sync_endpoint_with_cache(monkeypatch, isolated_db):
    """Testa o endpoint de sincronização sob demanda respeitando o cooldown."""
    monkeypatch.setattr("src.config.DATABASE_PATH", isolated_db)
    from src.database.seeds import seed_fixtures

    seed_fixtures(db_path=isolated_db)

    res = client.post("/api/v1/sync?days=30")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("cached", "success", "offline_fallback")
    assert data["snapshot"] is not None

