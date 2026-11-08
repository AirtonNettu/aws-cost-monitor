"""Coleta local com reserva diária transacional e registro de falhas."""
from datetime import datetime, timezone
import json
import logging

from src.analysis.cost_analyzer import analyze_costs
from src.analysis.finops_rules import generate_alerts
from src.aws.cost_explorer import get_costs
from src.database.repository import init_db, _get_connection, save_run

logger = logging.getLogger('cost_monitor.collection')


class CollectionBlocked(Exception):
    """Uma tentativa já ocorreu nesta data; não repetir automaticamente."""


def collect_once(db_path, *, days=30, tag=None):
    """Executa no máximo uma tentativa por dia UTC para este banco local."""
    init_db(db_path)
    key = datetime.now(timezone.utc).date().isoformat()
    now = datetime.now(timezone.utc).isoformat()
    with _get_connection(db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT status, run_id FROM collection_jobs WHERE job_key=?', (key,)).fetchone()
        if row:
            if row['status'] == 'succeeded':
                return row['run_id']
            raise CollectionBlocked('Tentativa diária já registrada; consulte o runbook.')
        conn.execute("INSERT INTO collection_jobs(job_key,status,started_at) VALUES (?, 'running', ?)", (key, now))
    try:
        costs = get_costs(period_days=days, granularity='DAILY', tag_key=tag)
        if not costs:
            raise ValueError('Coleta sem períodos para persistir.')
        analysis = analyze_costs(costs)
        run_id = save_run(costs, analysis, alerts=generate_alerts(analysis, None), db_path=db_path, tag=tag)
    except Exception:
        with _get_connection(db_path) as conn:
            conn.execute("UPDATE collection_jobs SET status='failed',finished_at=?,error_code='COLLECTION_FAILED' WHERE job_key=?", (datetime.now(timezone.utc).isoformat(), key))
        logger.error(json.dumps({'event': 'collection_finished', 'status': 'failed', 'error_code': 'COLLECTION_FAILED'}))
        raise
    with _get_connection(db_path) as conn:
        conn.execute("UPDATE collection_jobs SET status='succeeded',finished_at=?,run_id=? WHERE job_key=?", (datetime.now(timezone.utc).isoformat(), run_id, key))
    logger.info(json.dumps({'event': 'collection_finished', 'status': 'succeeded'}))
    return run_id
