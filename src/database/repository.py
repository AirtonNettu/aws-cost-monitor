"""Camada de persistência local em SQLite para histórico de custos.

Responsabilidade única: armazenar snapshots das execuções para habilitar
análise de tendências históricas e visualização no dashboard sem depender
de reconsultas à AWS.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from src import config


def _get_connection(db_path=None) -> sqlite3.Connection:
    path = db_path or config.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path=None) -> None:
    """Cria as tabelas e executa migrações incrementais de forma idempotente."""
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

        # Migração incremental: adiciona colunas de metadados se não existirem
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(runs)")
        existing_cols = {row["name"] for row in cursor.fetchall()}

        new_columns = [
            ("source", "TEXT NOT NULL DEFAULT 'aws'"),
            ("tag", "TEXT"),
            ("days", "INTEGER"),
            ("estimated", "INTEGER NOT NULL DEFAULT 0"),
            ("timeline_json", "TEXT"),
            ("comparison_json", "TEXT"),
            ("ai_json", "TEXT"),
            ("available_filters_json", "TEXT"),
            ("report_formats_json", "TEXT"),
        ]

        for col_name, col_def in new_columns:
            if col_name not in existing_cols:
                conn.execute(f"ALTER TABLE runs ADD COLUMN {col_name} {col_def}")

        # Índices para consultas eficientes, filtragem e ordenação
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs (created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_days_tag ON runs (days, tag)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_service_costs_run_id ON service_costs (run_id)")
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
    days=None,
    estimated=None,
    timeline=None,
    ai_state=None,
    report_formats=None,
    available_filters=None,
) -> int:
    """Grava o snapshot de uma execução no banco de dados SQLite.

    Retorna
    -------
    int
        O ID da execução recém-inserida.
    """
    init_db(db_path)

    period_start = costs[0]["start"] if costs else None
    period_end = costs[-1]["end"] if costs else None
    now_iso = datetime.now(timezone.utc).isoformat()

    prev_tot = comparison["previous_total"] if comparison else None
    variation = comparison["variation"] if comparison else None
    alerts_json = json.dumps(alerts or [], ensure_ascii=False)

    # Deriva days se não fornecido explicitamente
    if days is None and period_start and period_end:
        try:
            d_start = datetime.strptime(period_start, "%Y-%m-%d").date()
            d_end = datetime.strptime(period_end, "%Y-%m-%d").date()
            diff = (d_end - d_start).days
            if diff in {7, 30, 90}:
                days = diff
        except Exception:
            pass

    # Deriva flag estimated
    if estimated is None:
        estimated_val = 1 if (costs and any(c.get("estimated", False) for c in costs)) else 0
    else:
        estimated_val = 1 if estimated else 0

    # Deriva timeline
    if timeline is not None:
        timeline_json = json.dumps(timeline, ensure_ascii=False)
    elif costs:
        tl = []
        for c in costs:
            dt = c.get("start")
            amt = sum(
                float(g["Metrics"]["UnblendedCost"]["Amount"])
                for g in c.get("groups", [])
                if "Metrics" in g and "UnblendedCost" in g["Metrics"]
            )
            if dt:
                tl.append({"date": dt, "amount": round(amt, 2)})
        timeline_json = json.dumps(tl, ensure_ascii=False) if tl else None
    else:
        timeline_json = None

    # Deriva comparison_json estruturado
    if comparison is not None:
        prev_p = comparison.get("previous_period")
        if not prev_p and costs and len(costs) >= 2:
            prev_p = {"start": costs[-2]["start"], "end": costs[-2]["end"]}
        equiv = comparison.get("equivalent_periods")
        if equiv is None and prev_p and period_start and period_end:
            try:
                d1 = (datetime.strptime(prev_p["end"], "%Y-%m-%d") - datetime.strptime(prev_p["start"], "%Y-%m-%d")).days
                d2 = (datetime.strptime(period_end, "%Y-%m-%d") - datetime.strptime(period_start, "%Y-%m-%d")).days
                equiv = (d1 == d2 and d1 > 0)
            except Exception:
                equiv = False

        comp_dict = {
            "previous_total": float(prev_tot) if prev_tot is not None else 0.0,
            "current_total": float(comparison.get("current_total", analysis.get("total_cost", 0.0))),
            "variation": float(variation) if variation is not None else None,
            "equivalent_periods": bool(equiv),
            "previous_period": prev_p,
        }
        comparison_json = json.dumps(comp_dict, ensure_ascii=False)
    else:
        comparison_json = None

    # Deriva ai_json estruturado
    if ai_state is not None:
        if isinstance(ai_state, dict):
            ai_json = json.dumps(ai_state, ensure_ascii=False)
        else:
            ai_json = json.dumps(ai_state.model_dump(), ensure_ascii=False)
    else:
        ai_dict = {
            "status": "ready" if ai_interpretation else "unavailable",
            "text": ai_interpretation,
            "model": None,
            "observations": [],
            "recommendations": [],
            "potential_waste": [],
            "reason": None if ai_interpretation else "Análise ainda não executada.",
        }
        ai_json = json.dumps(ai_dict, ensure_ascii=False)

    # Formatos de relatório suportados
    report_formats_list = report_formats or ["json", "markdown", "html", "txt"]
    report_formats_json = json.dumps(report_formats_list, ensure_ascii=False)

    # Filtros disponíveis
    filters_dict = available_filters or {
        "days": [7, 30, 90],
        "tags": [tag] if tag else [],
    }
    available_filters_json = json.dumps(filters_dict, ensure_ascii=False)

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO runs (
                created_at, period_start, period_end, total_cost,
                has_positive_cost, largest_service, previous_total,
                variation, alerts_json, ai_interpretation,
                source, tag, days, estimated, timeline_json,
                comparison_json, ai_json, available_filters_json,
                report_formats_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                source,
                tag,
                days,
                estimated_val,
                timeline_json,
                comparison_json,
                ai_json,
                available_filters_json,
                report_formats_json,
            ),
        )
        run_id = cursor.lastrowid

        # Insere detalhamento dos serviços
        if analysis.get("has_positive_cost"):
            service_records = [
                (
                    run_id,
                    srv,
                    float(amt),
                    float(analysis.get("percentages", {}).get(srv, 0.0)),
                )
                for srv, amt in analysis.get("positive_services", {}).items()
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


def save_snapshot(snapshot: dict, db_path=None) -> int:
    """Insere um snapshot estruturado diretamente no SQLite."""
    init_db(db_path)
    period = snapshot["period"]
    period_start = period["start"]
    period_end = period["end"]
    try:
        d_start = datetime.strptime(period_start, "%Y-%m-%d").date()
        d_end = datetime.strptime(period_end, "%Y-%m-%d").date()
        days = (d_end - d_start).days
    except Exception:
        days = 30

    summary = snapshot["summary"]
    comparison = snapshot.get("comparison")
    prev_tot = comparison["previous_total"] if comparison else None
    variation = comparison["variation"] if comparison else None

    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO runs (
                created_at, period_start, period_end, total_cost,
                has_positive_cost, largest_service, previous_total,
                variation, alerts_json, ai_interpretation,
                source, tag, days, estimated, timeline_json,
                comparison_json, ai_json, available_filters_json,
                report_formats_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot["collected_at"],
                period_start,
                period_end,
                float(summary["total_cost"]),
                1 if summary["total_cost"] > 0 else 0,
                summary.get("largest_service"),
                float(prev_tot) if prev_tot is not None else None,
                float(variation) if variation is not None else None,
                json.dumps(snapshot.get("alerts", []), ensure_ascii=False),
                snapshot.get("ai", {}).get("text") if snapshot.get("ai") else None,
                snapshot.get("source", "aws"),
                snapshot.get("tag"),
                days,
                1 if snapshot.get("estimated") else 0,
                json.dumps(snapshot.get("timeline", []), ensure_ascii=False),
                json.dumps(comparison, ensure_ascii=False) if comparison else None,
                json.dumps(snapshot.get("ai", {}), ensure_ascii=False),
                json.dumps(snapshot.get("available_filters", {}), ensure_ascii=False),
                json.dumps(snapshot.get("report_formats", []), ensure_ascii=False),
            ),
        )
        run_id = cursor.lastrowid

        services = snapshot.get("services", [])
        if services:
            service_records = [
                (
                    run_id,
                    srv["name"],
                    float(srv["amount"]),
                    float(srv["percentage"]),
                )
                for srv in services
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


def get_latest_snapshot(days=30, tag=None, db_path=None) -> dict | None:
    """Busca o snapshot mais recente no SQLite com base no período (dias) e tag."""
    init_db(db_path)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        if tag:
            cursor.execute(
                """
                SELECT * FROM runs
                WHERE days = ? AND tag = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (days, tag),
            )
        else:
            cursor.execute(
                """
                SELECT * FROM runs
                WHERE days = ? AND (tag IS NULL OR tag = '')
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (days,),
            )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["alerts"] = json.loads(d["alerts_json"]) if d["alerts_json"] else []
        d["services"] = get_run_services(d["id"], db_path)
        return d


def get_run_by_id(run_id: int, db_path=None) -> dict | None:
    """Busca uma execução específica por ID."""
    init_db(db_path)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["alerts"] = json.loads(d["alerts_json"]) if d["alerts_json"] else []
        d["services"] = get_run_services(d["id"], db_path)
        return d


def get_history(limit=30, offset=0, tag=None, days=None, db_path=None) -> list[dict]:
    """Recupera o histórico recente de execuções com suporte a paginação e filtros."""
    init_db(db_path)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM runs"
        conditions = []
        params: list[Any] = []
        if days is not None:
            conditions.append("days = ?")
            params.append(days)
        if tag is not None:
            if tag == "":
                conditions.append("(tag IS NULL OR tag = '')")
            else:
                conditions.append("tag = ?")
                params.append(tag)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        cursor.execute(query, params)
        rows = cursor.fetchall()

    result = []
    for row in reversed(rows):
        d = dict(row)
        d["alerts"] = json.loads(d["alerts_json"]) if d["alerts_json"] else []
        result.append(d)
    return result


def get_available_tags(db_path=None) -> list[str]:
    """Retorna lista ordenada de tags distintas registradas."""
    init_db(db_path)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT tag FROM runs WHERE tag IS NOT NULL AND tag != '' ORDER BY tag"
        )
        return [row[0] for row in cursor.fetchall()]


def get_available_days(db_path=None) -> list[int]:
    """Retorna os períodos em dias distintos registrados."""
    init_db(db_path)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT days FROM runs WHERE days IS NOT NULL ORDER BY days"
        )
        days = [row[0] for row in cursor.fetchall() if row[0] in {7, 30, 90}]
        return days if days else [7, 30, 90]


def get_run_services(run_id, db_path=None) -> list[dict]:
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


def get_latest_run(db_path=None) -> dict | None:
    """Retorna a última execução gravada ou None se a tabela estiver vazia."""
    init_db(db_path)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM runs
            ORDER BY created_at DESC, id DESC
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
