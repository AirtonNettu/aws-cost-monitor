"""Exporta uma resposta HTTP validada da API local com dados sintéticos."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import secrets
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from scripts.seed_demo import seed
from src.api.app import create_app, Settings

with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / "demo.db"
    seed(path)
    password = secrets.token_urlsafe(24)
    with TestClient(create_app(Settings(path, "operator", password))) as client:
        response = client.get(
            "/api/v1/snapshots/latest?days=30", auth=("operator", password)
        )
        response.raise_for_status()
        print(json.dumps(response.json(), ensure_ascii=False))
