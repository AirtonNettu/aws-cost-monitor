"""Script utilitário para popular data/costs.db com snapshots sintéticos.

Permite testar e integrar o frontend React contra a API FastAPI local
sem necessidade de credenciais ou consultas com custo à AWS.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Adiciona a raiz do projeto ao sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import config
from src.database.seeds import seed_fixtures


def main():
    print("Iniciando semeadura de snapshots sintéticos no SQLite...")
    db_path = config.DATABASE_PATH
    ids = seed_fixtures(db_path=db_path)
    print(f"Sucesso! {len(ids)} snapshots sintéticos gravados em {db_path}.")


if __name__ == "__main__":
    main()
