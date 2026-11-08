"""Camada de persistência local em SQLite para histórico de custos.

Responsabilidade única: armazenar snapshots das execuções para habilitar
análise de tendências históricas e visualização no dashboard sem depender
de reconsultas à AWS.
"""

import json
import os
import sqlite3
from datetime import datetime

from src import config


def _get_connection(db_path=None):
    path = db_path or config.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db(db_path=None):
    """Cria as tabelas necessárias no SQLite se não existirem."""
    with _get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
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
            CREATE TABLE IF NOT EXISTS service_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                service_name TEXT NOT NULL,
                amount REAL NOT NULL,
                percentage REAL NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs (id) ON DELETE CASCADE
            )
        """)
        conn.execute("""CREATE TABLE IF NOT EXISTS snapshots (
            run_id INTEGER PRIMARY KEY REFERENCES runs(id) ON DELETE CASCADE,
            period_days INTEGER NOT NULL, tag TEXT, source TEXT NOT NULL,
            collected_at TEXT NOT NULL, payload TEXT NOT NULL)""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS snapshots_filters ON snapshots(period_days, tag, collected_at)"
        )
        conn.execute("""CREATE TABLE IF NOT EXISTS collection_jobs (
            job_key TEXT PRIMARY KEY, status TEXT NOT NULL, started_at TEXT NOT NULL,
            finished_at TEXT, error_code TEXT, run_id INTEGER, request_json TEXT)""")
        columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(collection_jobs)")
        }
        if "run_id" not in columns:
            conn.execute("ALTER TABLE collection_jobs ADD COLUMN run_id INTEGER")
        if "request_json" not in columns:
            conn.execute("ALTER TABLE collection_jobs ADD COLUMN request_json TEXT")
        conn.commit()


def save_run(
    costs,
    analysis,
    comparison=None,
    ai_interpretation=None,
    alerts=None,
    db_path=None,
    *,
    source="aws",
    tag=None,
    collected_at=None,
):
    """Grava o snapshot de uma execução no banco de dados SQLite.

    Retorna
    -------
    int
        O ID da execução recém-inserida.
    """
    init_db(db_path)
    from src.application.snapshots import Summary

    Summary(
        total_cost=analysis["total_cost"],
        largest_service=analysis["largest_service"],
        largest_service_percentage=analysis["percentages"].get(
            analysis["largest_service"]
        ),
        alert_count=len(alerts or []),
    )

    period_start = costs[0]["start"] if costs else None
    period_end = costs[-1]["end"] if costs else None
    now_iso = datetime.now().isoformat()

    prev_tot = comparison["previous_total"] if comparison else None
    variation = comparison["variation"] if comparison else None
    alerts_json = json.dumps(alerts or [], ensure_ascii=False)

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO runs (
                created_at, period_start, period_end, total_cost,
                has_positive_cost, largest_service, previous_total,
                variation, alerts_json, ai_interpretation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_iso,
                period_start,
                period_end,
                float(analysis["total_cost"]),
                1 if analysis["has_positive_cost"] else 0,
                analysis["largest_service"],
                float(prev_tot) if prev_tot is not None else None,
                float(variation) if variation is not None else None,
                alerts_json,
                ai_interpretation,
            ),
        )
        run_id = cursor.lastrowid

        # Insere detalhamento dos serviços
        if analysis["has_positive_cost"]:
            service_records = [
                (
                    run_id,
                    srv,
                    float(amt),
                    float(analysis["percentages"].get(srv, 0.0)),
                )
                for srv, amt in analysis["positive_services"].items()
            ]
            cursor.executemany(
                """
                INSERT INTO service_costs (run_id, service_name, amount, percentage)
                VALUES (?, ?, ?, ?)
                """,
                service_records,
            )

        if costs:
            from src.application.snapshots import build_snapshot, Snapshot

            previous_row = conn.execute(
                "SELECT payload FROM snapshots WHERE tag IS ? AND source=? AND period_days=? AND json_extract(payload, '$.period.end')=? ORDER BY collected_at DESC, run_id DESC LIMIT 1",
                (
                    tag,
                    source,
                    (
                        datetime.fromisoformat(max(p["end"] for p in costs))
                        - datetime.fromisoformat(min(p["start"] for p in costs))
                    ).days,
                    min(p["start"] for p in costs),
                ),
            ).fetchone()
            previous = (
                Snapshot.model_validate_json(previous_row["payload"])
                if previous_row
                else None
            )
            snapshot = build_snapshot(
                run_id,
                costs,
                analysis,
                ai_interpretation,
                source=source,
                tag=tag,
                collected_at=collected_at,
                previous=previous,
            )
            conn.execute(
                "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    (snapshot.period.end - snapshot.period.start).days,
                    tag,
                    source,
                    snapshot.collected_at.isoformat(),
                    snapshot.model_dump_json(),
                ),
            )
        conn.commit()
        return run_id


def get_history(limit=30, db_path=None):
    """Recupera o histórico recente de execuções ordenado cronologicamente."""
    init_db(db_path)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, created_at, period_start, period_end, total_cost,
                   has_positive_cost, largest_service, previous_total,
                   variation, alerts_json, ai_interpretation
            FROM runs
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()

    result = []
    for row in reversed(rows):
        d = dict(row)
        d["alerts"] = json.loads(d["alerts_json"]) if d["alerts_json"] else []
        result.append(d)
    return result


def get_run_services(run_id, db_path=None):
    """Retorna os serviços registrados para uma execução específica."""
    init_db(db_path)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT service_name, amount, percentage
            FROM service_costs
            WHERE run_id = ?
            ORDER BY amount DESC
            """,
            (run_id,),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_latest_run(db_path=None):
    """Retorna a última execução gravada ou None se a tabela estiver vazia."""
    init_db(db_path)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, created_at, period_start, period_end, total_cost,
                   has_positive_cost, largest_service, previous_total,
                   variation, alerts_json, ai_interpretation
            FROM runs
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["alerts"] = json.loads(d["alerts_json"]) if d["alerts_json"] else []
        d["services"] = get_run_services(d["id"], db_path)
        return d
