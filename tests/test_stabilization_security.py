"""Revisão de autenticação, CORS e falhas de armazenamento sem segredos reais."""

import sqlite3
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from src.api.app import Settings, create_app
from scripts.seed_demo import seed


@pytest.fixture
def api(tmp_path):
    path = tmp_path / "data.db"
    seed(path)
    with TestClient(
        create_app(Settings(path, "operator", "credencial-sintetica-teste"))
    ) as client:
        yield client, path


@pytest.mark.parametrize(
    "route",
    [
        "/api/v1/runs",
        "/api/v1/snapshots/latest",
        "/api/v1/runs/4",
        "/api/v1/runs/4/reports/json",
        "/api/v1/runs/4/reports/csv",
        "/health/ready",
        "/api/v1/openapi.json",
    ],
)
def test_todas_as_leituras_privadas_exigem_autenticacao(api, route):
    client, _ = api
    response = client.get(route)
    assert response.status_code == 401
    assert "Amazon EC2" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_cors_nao_autoriza_origem_arbitraria(api):
    client, _ = api
    response = client.options(
        "/api/v1/runs",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_logs_e_erros_nao_repetem_entrada_privada(api):
    client, _ = api
    with patch("src.api.app.logger.info") as log:
        response = client.get(
            "/api/v1/runs?limit=CONTEXTO_PRIVADO",
            auth=("operator", "credencial-sintetica-teste"),
        )
        assert response.status_code == 422
        assert "CONTEXTO_PRIVADO" not in response.text
        assert "CONTEXTO_PRIVADO" not in str(log.call_args_list)
        assert "credencial-sintetica-teste" not in str(log.call_args_list)


@pytest.mark.parametrize("payload", ["not-json", "[]", "{}"])
def test_payload_corrompido_produz_erro_seguro_503(api, payload):
    client, path = api
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE snapshots SET payload=? WHERE run_id=4", (payload,))
    response = client.get(
        "/api/v1/runs/4", auth=("operator", "credencial-sintetica-teste")
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "INVALID_SNAPSHOT"
