"""Recuperação local com SQLite temporário, sem chamadas externas."""

from unittest.mock import patch
import sqlite3
import pytest
from src.operations import collection


def test_recuperacao_explicita_limitada(tmp_path, costs_single_period):
    path = tmp_path / "jobs.db"
    with patch.object(collection, "get_costs", side_effect=RuntimeError("privado")):
        with pytest.raises(RuntimeError):
            collection.collect_once(path)
    job = collection.inspect_job(path)
    assert job["status"] == "failed"
    with patch.object(collection, "get_costs", return_value=costs_single_period) as aws:
        with pytest.raises(collection.CollectionBlocked):
            collection.recover_once(
                path, expected_token=job["attempt_token"], confirm_stopped=False
            )
        result = collection.recover_once(
            path, expected_token=job["attempt_token"], confirm_stopped=True
        )
        assert collection.collect_once(path) == result
        assert aws.call_count == 1
    assert collection.inspect_job(path)["attempts"] == 2
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM snapshots").fetchone()[0] == 1


def test_duas_falhas_nao_autorizam_terceira_tentativa(tmp_path):
    path = tmp_path / "jobs.db"
    with patch.object(
        collection, "get_costs", side_effect=RuntimeError("privado")
    ) as aws:
        with pytest.raises(RuntimeError):
            collection.collect_once(path)
        job = collection.inspect_job(path)
        with pytest.raises(RuntimeError):
            collection.recover_once(
                path, expected_token=job["attempt_token"], confirm_stopped=True
            )
        job = collection.inspect_job(path)
        with pytest.raises(collection.CollectionBlocked):
            collection.recover_once(
                path, expected_token=job["attempt_token"], confirm_stopped=True
            )
        assert aws.call_count == 2


def test_erro_antes_do_commit_nao_deixa_snapshot_orfao(tmp_path, costs_single_period):
    path = tmp_path / "jobs.db"
    original = collection.save_run

    def interrupted(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("interrupção antes da conclusão")

    with (
        patch.object(collection, "get_costs", return_value=costs_single_period),
        patch.object(collection, "save_run", side_effect=interrupted),
    ):
        with pytest.raises(RuntimeError):
            collection.collect_once(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT count(*) FROM snapshots").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM runs").fetchone()[0] == 0
    assert collection.inspect_job(path)["status"] == "failed"


def test_recuperacao_rejeita_token_obsoleto(tmp_path, costs_single_period):
    path = tmp_path / "jobs.db"
    with patch.object(collection, "get_costs", side_effect=RuntimeError("privado")):
        with pytest.raises(RuntimeError):
            collection.collect_once(path)
    with patch.object(collection, "get_costs") as aws:
        with pytest.raises(collection.CollectionBlocked):
            collection.recover_once(
                path, expected_token="obsoleto", confirm_stopped=True
            )
        aws.assert_not_called()


def test_escritor_ativo_impede_recuperacao(tmp_path, costs_single_period):
    """Reproduz a disputa real de locks sem aguardar timeout longo no teste."""
    from src.database.repository import _get_connection

    path = tmp_path / "jobs.db"
    with patch.object(collection, "get_costs", side_effect=RuntimeError("privado")):
        with pytest.raises(RuntimeError):
            collection.collect_once(path)
    job = collection.inspect_job(path)
    writer = _get_connection(path)
    writer.execute("BEGIN IMMEDIATE")

    def short_connection(db):
        conn = _get_connection(db)
        conn.execute("PRAGMA busy_timeout=1")
        return conn

    try:
        with (
            patch.object(collection, "_get_connection", side_effect=short_connection),
            patch.object(collection, "get_costs") as aws,
        ):
            with pytest.raises(collection.CollectionBlocked):
                collection.recover_once(
                    path, expected_token=job["attempt_token"], confirm_stopped=True
                )
            aws.assert_not_called()
    finally:
        writer.rollback()
        writer.close()
