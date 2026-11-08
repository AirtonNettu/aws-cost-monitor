"""Contrato HTTP e persistência sem acesso a serviços externos."""
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from src.analysis.cost_analyzer import analyze_costs
from src.database.repository import save_run


def test_snapshot_persistido_com_creditos(tmp_path, costs_single_period):
    """A gravação legada também deve produzir um snapshot completo e válido."""
    path = tmp_path / 'costs.db'
    run_id = save_run(costs_single_period, analyze_costs(costs_single_period), db_path=path)
    with sqlite3.connect(path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert 'snapshots' in tables
        payload = json.loads(conn.execute('SELECT payload FROM snapshots WHERE run_id=?', (run_id,)).fetchone()[0])
    assert payload['summary']['total_cost'] == 50
    assert payload['period'] == {'start': '2026-08-01', 'end': '2026-09-01'}
    assert payload['comparison'] is None
    assert payload['timeline'] == []


def test_api_leitura_autenticada(tmp_path, costs_single_period):
    """Rotas de dados exigem o operador e jamais chamam AWS ou Ollama."""
    from fastapi.testclient import TestClient
    from src.api.app import create_app, Settings
    path = tmp_path / 'api.db'
    save_run(costs_single_period, analyze_costs(costs_single_period), db_path=path)
    with patch('boto3.client', side_effect=AssertionError('AWS proibida')):
        with TestClient(create_app(Settings(path, 'operator', 'senha-sintetica-de-teste'))) as client:
            assert client.get('/health/live').status_code == 200
            unauthorized = client.get('/api/v1/runs')
            assert unauthorized.status_code == 401
            assert unauthorized.json()['error']['code'] == 'UNAUTHORIZED'
            assert client.get('/api/v1/runs', auth=('other', 'senha-sintetica-de-teste')).status_code == 401
            auth = ('operator', 'senha-sintetica-de-teste')
            history = client.get('/api/v1/runs', auth=auth)
            assert len(history.json()['runs']) == 1
            detail = client.get('/api/v1/runs/1', auth=auth)
            assert detail.status_code == 200
            assert detail.json()['summary']['total_cost'] == 50
            assert 'AWS_SECRET_ACCESS_KEY' not in detail.text
            assert client.get('/api/v1/snapshots/latest?days=30', auth=auth).status_code == 404
            assert client.get('/api/v1/runs?limit=1000', auth=auth).status_code == 422
            assert client.get('/api/v1/runs/999', auth=auth).status_code == 404
            assert client.get('/api/v1/runs/1/reports/html', auth=auth).status_code == 422
            assert client.get('/api/v1/runs/1/reports/json', auth=auth).json()['id'] == '1'
            assert client.get('/api/v1/runs/1/reports/csv', auth=auth).headers['content-disposition'].startswith('attachment;')
            assert client.get('/health/ready', auth=auth).status_code == 200
            assert detail.headers['cache-control'] == 'no-store'


def test_api_recusa_configuracao_insegura(tmp_path):
    from src.api.app import create_app, Settings
    with pytest.raises(ValueError):
        create_app(Settings(tmp_path / 'a.db', 'operator', ''))
