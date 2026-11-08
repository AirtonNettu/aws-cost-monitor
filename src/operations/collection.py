"""Reserva diária durável, conclusão atômica e recuperação administrativa limitada."""

import json
import logging
import sqlite3
from contextlib import closing, contextmanager
from datetime import UTC, date, datetime
from uuid import uuid4

from src import config
from src.analysis.cost_analyzer import analyze_costs
from src.analysis.finops_rules import generate_alerts
from src.aws.cost_explorer import get_costs
from src.database.repository import _get_connection, init_db, save_run

logger = logging.getLogger("cost_monitor.collection")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
MAX_ATTEMPTS = 2


class CollectionBlocked(Exception):
    """Reserva existente ou escritor ativo impede execução/reabertura insegura."""


@contextmanager
def transaction(path):
    """Exclui escritores concorrentes sem liberar o proprietário durante a coleta."""
    try:
        with closing(_get_connection(path)) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
    except sqlite3.OperationalError as error:
        if getattr(error, "sqlite_errorcode", 0) & 255 in (
            sqlite3.SQLITE_BUSY,
            sqlite3.SQLITE_LOCKED,
        ):
            raise CollectionBlocked(
                "Escritor ativo; não recuperar nem executar simultaneamente."
            ) from error
        raise


def _now():
    return datetime.now(UTC).isoformat()


def _event(event, attempt):
    """Não registra escopo, caminhos, resposta financeira ou exceção original."""
    logger.info(json.dumps({"event": event, "attempt": attempt}))


def inspect_job(db_path):
    """Mostra somente metadados operacionais da reserva do dia UTC atual."""
    from src.database.snapshots import connection

    key = datetime.now(UTC).date().isoformat()
    with connection(db_path) as conn:
        row = conn.execute(
            "SELECT job_key,status,attempts,attempt_token,started_at,finished_at,error_code,run_id FROM collection_jobs WHERE job_key=?",
            (key,),
        ).fetchone()
    return dict(row) if row else None


def _execute(db_path, key, token):
    attempt = 0
    try:
        with transaction(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM collection_jobs WHERE job_key=?", (key,)
            ).fetchone()
            if not row or row["status"] != "running" or row["attempt_token"] != token:
                raise CollectionBlocked("A tentativa não possui mais esta reserva.")
            attempt = row["attempts"]
            scope = json.loads(row["request_json"])
            # String vazia desativa explicitamente o fallback de tag do adaptador.
            costs = get_costs(
                period_days=scope["days"],
                granularity="DAILY",
                tag_key=scope["tag"] or "",
                end_date=date.fromisoformat(key),
            )
            if not costs:
                raise ValueError("Coleta sem períodos para persistir.")
            analysis = analyze_costs(costs)
            run_id = save_run(
                costs,
                analysis,
                alerts=generate_alerts(analysis, None),
                db_path=db_path,
                tag=scope["tag"],
                _connection=conn,
            )
            conn.execute(
                "UPDATE collection_jobs SET status='succeeded',finished_at=?,run_id=? WHERE job_key=? AND attempt_token=?",
                (_now(), run_id, key, token),
            )
        _event("collection_succeeded", attempt)
        return run_id
    except Exception:
        # Rollback inclui snapshot e conclusão; processo obsoleto não altera o novo dono.
        with transaction(db_path) as conn:
            conn.execute(
                "UPDATE collection_jobs SET status='failed',finished_at=?,error_code='COLLECTION_FAILED' WHERE job_key=? AND status='running' AND attempt_token=?",
                (_now(), key, token),
            )
        _event("collection_failed", attempt)
        raise


def collect_once(db_path, *, days=30, tag=None):
    """Reserva uma tentativa diária; falhas nunca são repetidas automaticamente."""
    tag = config.COST_TAG_KEY if tag is None else tag
    scope = json.dumps({"days": days, "tag": tag or None}, sort_keys=True)
    init_db(db_path)
    key = datetime.now(UTC).date().isoformat()
    token = str(uuid4())
    with transaction(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM collection_jobs WHERE job_key=?", (key,)
        ).fetchone()
        if row:
            if row["status"] == "succeeded" and row["request_json"] == scope:
                return row["run_id"]
            raise CollectionBlocked(
                "Reserva diária existente; consulte status e runbook."
            )
        conn.execute(
            "INSERT INTO collection_jobs(job_key,status,started_at,request_json,attempts,attempt_token) VALUES (?, 'running', ?, ?, 1, ?)",
            (key, _now(), scope, token),
        )
    _event("collection_reserved", 1)
    return _execute(db_path, key, token)


def recover_once(db_path, *, expected_token, confirm_stopped=False):
    """Recupera somente a reserva atual, com exclusão mútua e uma repetição manual."""
    if not confirm_stopped or not expected_token:
        raise CollectionBlocked(
            "Confirme a parada do processo e informe o token observado."
        )
    key = datetime.now(UTC).date().isoformat()
    token = str(uuid4())
    with transaction(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM collection_jobs WHERE job_key=?", (key,)
        ).fetchone()
        if (
            not row
            or row["attempt_token"] != expected_token
            or row["status"] not in ("failed", "running")
            or row["attempts"] >= MAX_ATTEMPTS
            or not row["request_json"]
            or row["run_id"] is not None
        ):
            raise CollectionBlocked(
                "Reserva alterada, legada, concluída ou limite de tentativas atingido."
            )
        conn.execute(
            "UPDATE collection_jobs SET status='running',attempts=attempts+1,attempt_token=?,started_at=?,finished_at=NULL,error_code=NULL WHERE job_key=?",
            (token, _now(), key),
        )
        attempt = row["attempts"] + 1
    _event("collection_recovery_authorized", attempt)
    return _execute(db_path, key, token)
