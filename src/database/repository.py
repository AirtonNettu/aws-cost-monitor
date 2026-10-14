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
        conn.commit()


def save_run(
    costs,
    analysis,
    comparison=None,
    ai_interpretation=None,
    alerts=None,
    db_path=None,
):
    """Grava o snapshot de uma execução no banco de dados SQLite.

    Retorna
    -------
    int
        O ID da execução recém-inserida.
    """
    init_db(db_path)

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
