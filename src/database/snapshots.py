"""Consultas somente leitura; não inicializam nem modificam bancos existentes."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.application.snapshots import Snapshot, RunSummary, History, Filters


@contextmanager
def connection(path):
    """Abre o banco com modo somente leitura e timeout finito."""
    conn = sqlite3.connect(
        Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=5
    )
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def available(conn):
    """Anuncia somente filtros com snapshots persistidos."""
    rows = conn.execute("SELECT DISTINCT period_days, tag FROM snapshots").fetchall()
    return {
        "days": sorted(
            {r["period_days"] for r in rows if r["period_days"] in (7, 30, 90)}
        ),
        "tags": sorted({r["tag"] for r in rows if r["tag"]}),
    }


def get_snapshot(path, *, run_id=None, days=None, tag=None):
    """Seleciona por identificador ou intervalo/escopo exatos."""
    with connection(path) as conn:
        if run_id is not None:
            row = conn.execute(
                "SELECT payload FROM snapshots WHERE run_id=?", (run_id,)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT payload FROM snapshots WHERE period_days=? AND tag IS ? ORDER BY collected_at DESC, run_id DESC LIMIT 1",
                (days, tag),
            ).fetchone()
        if row is None:
            raise LookupError("Snapshot não encontrado.")
        snapshot = Snapshot.model_validate_json(row["payload"])
        return snapshot.model_copy(
            update={"available_filters": Filters.model_validate(available(conn))}
        )


def list_snapshots(path, limit=50):
    """Retorna o histórico de snapshots completos, mais recentes primeiro."""
    with connection(path) as conn:
        rows = conn.execute(
            "SELECT payload FROM snapshots ORDER BY collected_at DESC, run_id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    runs = []
    for row in rows:
        snapshot = Snapshot.model_validate_json(row["payload"])
        runs.append(
            RunSummary(
                id=snapshot.id,
                collected_at=snapshot.collected_at,
                period=snapshot.period,
                estimated=snapshot.estimated,
                total_cost=snapshot.summary.total_cost,
                largest_service=snapshot.summary.largest_service,
            )
        )
    return History(runs=runs)
