"""Utilitário de carga de dados sintéticos para testes e desenvolvimento do frontend.

Carrega fixtures realistas sem realizar qualquer chamada com custo à AWS.
"""

from __future__ import annotations

import json
from pathlib import Path

from src import config
from src.database.repository import init_db, save_snapshot


def get_default_fixtures_path() -> Path:
    """Localiza o arquivo de fixtures gerado para o frontend."""
    return (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "src"
        / "mocks"
        / "fixtures.json"
    )


def seed_fixtures(db_path=None, fixtures_path=None) -> list[int]:
    """Popula o banco SQLite com snapshots sintéticos baseados em fixtures.json.

    Retorna a lista de IDs inseridos.
    """
    path = fixtures_path or get_default_fixtures_path()
    if not Path(path).exists():
        raise FileNotFoundError(f"Arquivo de fixtures não encontrado: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    init_db(db_path)
    inserted_ids = []

    # 1. Insere os snapshots chaveados por período/tag
    snapshots_map = data.get("snapshots", {})
    for _key, snapshot in snapshots_map.items():
        run_id = save_snapshot(snapshot, db_path=db_path)
        inserted_ids.append(run_id)

    # 2. Insere execuções do histórico
    for run in data.get("runs", []):
        run_id = save_snapshot(run, db_path=db_path)
        inserted_ids.append(run_id)

    return inserted_ids
