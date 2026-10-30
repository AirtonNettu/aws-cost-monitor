"""Camada de persistência local em SQLite para histórico de custos.

Responsabilidade única: armazenar snapshots das execuções para habilitar
análise de tendências históricas e visualização no dashboard sem depender
de reconsultas à AWS.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

from src import config


def ensure_finite_float(val: Any, field_name: str = "valor", allow_none: bool = False) -> float | None:
    """Garante que um valor financeiro seja um float finito válido.

    - Rejeita estritamente NaN, Infinity e -Infinity levantando ValueError.
    - Rejeita valores não numéricos sem converter silenciosamente para zero.
    - Preserva números negativos (ex: créditos e estornos da AWS).
    """
    if val is None:
        if allow_none:
            return None
        raise ValueError(f"Campo financeiro '{field_name}' não pode ser nulo.")

    try:
        num = float(val)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Campo financeiro '{field_name}' inválido: valor '{val!r}' não pode ser convertido para número."
        ) from exc

    if not math.isfinite(num):
        raise ValueError(
            f"Campo financeiro '{field_name}' inválido: valores NaN e Infinito são proibidos (recebido: {val})."
        )

    return num


def check_period_equivalence(
    curr_start: str | None,
    curr_end: str | None,
    prev_start: str | None,
    prev_end: str | None,
    curr_scope: str | None = None,
    prev_scope: str | None = None,
) -> bool:
    """Valida se dois períodos e seus respectivos escopos são efetivamente comparáveis.

    Regras de equivalência:
    1. Metadados completos: datas de início e fim presentes e em formato ISO YYYY-MM-DD.
    2. Validade temporal: start < end em ambos os intervalos.
    3. Duração idêntica: exatamente o mesmo número de dias em ambos os períodos.
    4. Sem sobreposição: o período anterior deve terminar antes ou no máximo no início do período atual (prev_end <= curr_start).
    5. Escopo idêntico: se tags/filtros forem definidos, devem ser estritamente iguais.
    """
    if not (curr_start and curr_end and prev_start and prev_end):
        return False

    clean_curr_scope = curr_scope.strip() if curr_scope and curr_scope.strip() else None
    clean_prev_scope = prev_scope.strip() if prev_scope and prev_scope.strip() else None
    if clean_curr_scope != clean_prev_scope:
        return False

    try:
        c_start = datetime.strptime(curr_start, "%Y-%m-%d").date()
        c_end = datetime.strptime(curr_end, "%Y-%m-%d").date()
        p_start = datetime.strptime(prev_start, "%Y-%m-%d").date()
        p_end = datetime.strptime(prev_end, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return False

    if c_start >= c_end or p_start >= p_end:
        return False

    d_curr = (c_end - c_start).days
    d_prev = (p_end - p_start).days
    if d_curr != d_prev or d_curr <= 0:
        return False

    # Intervalos sobrepostos não são comparáveis como períodos sequenciais
    if p_end > c_start:
        return False

    return True


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

    # Validação rigorosa dos valores financeiros de nível superior
    total_cost_clean = ensure_finite_float(analysis["total_cost"], "total_cost")
    prev_tot = (
        ensure_finite_float(comparison["previous_total"], "previous_total", allow_none=True)
        if comparison
        else None
    )
    variation = (
        ensure_finite_float(comparison["variation"], "variation", allow_none=True)
        if comparison
        else None
    )
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

    # Deriva timeline com validação de números finitos
    if timeline is not None:
        validated_tl = [
            {
                "date": str(item["date"]),
                "amount": ensure_finite_float(item["amount"], "timeline amount"),
            }
            for item in timeline
        ]
        timeline_json = json.dumps(validated_tl, ensure_ascii=False)
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
                tl.append({"date": dt, "amount": ensure_finite_float(round(amt, 2), "timeline amount")})
        timeline_json = json.dumps(tl, ensure_ascii=False) if tl else None
    else:
        timeline_json = None

    # Deriva comparison_json estruturado com validação de equivalência estrita
    if comparison is not None:
        prev_p = comparison.get("previous_period")
        if not prev_p and costs and len(costs) >= 2:
            prev_p = {"start": costs[-2]["start"], "end": costs[-2]["end"]}

        prev_scope = comparison.get("previous_scope", tag)

        equiv = check_period_equivalence(
            curr_start=period_start,
            curr_end=period_end,
            prev_start=prev_p.get("start") if prev_p else None,
            prev_end=prev_p.get("end") if prev_p else None,
            curr_scope=tag,
            prev_scope=prev_scope,
        )

        valid_prev_period = False
        if prev_p and prev_p.get("start") and prev_p.get("end"):
            try:
                ps = datetime.strptime(prev_p["start"], "%Y-%m-%d").date()
                pe = datetime.strptime(prev_p["end"], "%Y-%m-%d").date()
                if ps < pe:
                    valid_prev_period = True
            except Exception:
                valid_prev_period = False

        if valid_prev_period:
            comp_dict = {
                "previous_total": prev_tot if prev_tot is not None else 0.0,
                "current_total": ensure_finite_float(
                    comparison.get("current_total", total_cost_clean), "current_total"
                ),
                "variation": variation,
                "equivalent_periods": equiv,
                "previous_period": {"start": prev_p["start"], "end": prev_p["end"]},
            }
            comparison_json = json.dumps(comp_dict, ensure_ascii=False)
        else:
            comparison_json = None
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

    report_formats_list = report_formats or ["json", "markdown", "html", "txt"]
    report_formats_json = json.dumps(report_formats_list, ensure_ascii=False)

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
                total_cost_clean,
                1 if analysis.get("has_positive_cost") else (1 if total_cost_clean > 0 else 0),
                analysis.get("largest_service"),
                prev_tot,
                variation,
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

        # Insere detalhamento dos serviços com validação de floats finitos
        # Aceita valores negativos (ex: créditos e reembolsos de serviços da AWS)
        positive_services = analysis.get("positive_services", {})
        all_services = analysis.get("services", positive_services)
        services_to_insert = positive_services if analysis.get("has_positive_cost") else all_services

        if services_to_insert:
            service_records = [
                (
                    run_id,
                    srv,
                    ensure_finite_float(amt, f"amount do serviço '{srv}'"),
                    ensure_finite_float(
                        analysis.get("percentages", {}).get(srv, 0.0),
                        f"percentage do serviço '{srv}'",
                    ),
                )
                for srv, amt in services_to_insert.items()
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
    """Insere um snapshot estruturado diretamente no SQLite com validações estritas."""
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
    total_cost_clean = ensure_finite_float(summary["total_cost"], "summary.total_cost")

    comparison = snapshot.get("comparison")
    prev_tot = (
        ensure_finite_float(comparison["previous_total"], "comparison.previous_total", allow_none=True)
        if comparison
        else None
    )
    variation = (
        ensure_finite_float(comparison["variation"], "comparison.variation", allow_none=True)
        if comparison
        else None
    )

    # Valida equivalência se houver comparison
    comparison_to_save = None
    if comparison and comparison.get("previous_period"):
        prev_p = comparison["previous_period"]
        equiv = check_period_equivalence(
            curr_start=period_start,
            curr_end=period_end,
            prev_start=prev_p.get("start"),
            prev_end=prev_p.get("end"),
            curr_scope=snapshot.get("tag"),
            prev_scope=comparison.get("previous_scope", snapshot.get("tag")),
        )
        try:
            ps = datetime.strptime(prev_p["start"], "%Y-%m-%d").date()
            pe = datetime.strptime(prev_p["end"], "%Y-%m-%d").date()
            if ps < pe:
                comparison_to_save = {
                    "previous_total": prev_tot if prev_tot is not None else 0.0,
                    "current_total": ensure_finite_float(
                        comparison.get("current_total", total_cost_clean), "comparison.current_total"
                    ),
                    "variation": variation,
                    "equivalent_periods": equiv,
                    "previous_period": {"start": prev_p["start"], "end": prev_p["end"]},
                }
        except Exception:
            comparison_to_save = None

    # Validação da timeline
    validated_tl = [
        {
            "date": str(item["date"]),
            "amount": ensure_finite_float(item["amount"], "timeline amount"),
        }
        for item in snapshot.get("timeline", [])
    ]

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
                total_cost_clean,
                1 if total_cost_clean > 0 else 0,
                summary.get("largest_service"),
                prev_tot,
                variation,
                json.dumps(snapshot.get("alerts", []), ensure_ascii=False),
                snapshot.get("ai", {}).get("text") if snapshot.get("ai") else None,
                snapshot.get("source", "aws"),
                snapshot.get("tag"),
                days,
                1 if snapshot.get("estimated") else 0,
                json.dumps(validated_tl, ensure_ascii=False),
                json.dumps(comparison_to_save, ensure_ascii=False) if comparison_to_save else None,
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
                    ensure_finite_float(srv["amount"], f"amount do serviço '{srv['name']}'"),
                    ensure_finite_float(srv["percentage"], f"percentage do serviço '{srv['name']}'"),
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


def get_history(
    limit: int = 30,
    offset: int = 0,
    tag: str | None = None,
    days: int | None = None,
    only_compatible: bool = False,
    order_desc: bool = False,
    db_path: str | None = None,
) -> list[dict]:
    """Recupera o histórico recente de execuções com suporte a paginação e filtros.

    Parâmetros
    ----------
    only_compatible : bool
        Se True, filtra no SQLite apenas registros que atendem aos requisitos da API
        (período definido e timestamp com fuso offset/Z), garantindo paginação consistente.
    order_desc : bool
        Se True, retorna na ordem mais recente para o mais antigo (newest first).
        Se False, preserva a ordem cronológica legada (oldest first).
    """
    init_db(db_path)
    with _get_connection(db_path) as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM runs"
        conditions = []
        params: list[Any] = []

        if only_compatible:
            conditions.append("period_start IS NOT NULL AND period_start != ''")
            conditions.append("period_end IS NOT NULL AND period_end != ''")
            conditions.append(
                "(created_at LIKE '%+%' OR created_at LIKE '%Z' OR SUBSTR(created_at, 20) LIKE '-%')"
            )

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
    iterable = rows if order_desc else reversed(rows)
    for row in iterable:
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
