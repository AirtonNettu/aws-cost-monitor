"""Read-only API contract smoke tests; no real AWS or Ollama requests."""

from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_latest_is_explicitly_unimplemented():
    response = client.get("/api/v1/snapshots/latest?days=30")
    assert response.status_code == 501


def test_invalid_days_rejected():
    response = client.get("/api/v1/snapshots/latest?days=999")
    assert response.status_code == 422


def test_invalid_limit_rejected():
    response = client.get("/api/v1/runs?limit=0")
    assert response.status_code == 422
