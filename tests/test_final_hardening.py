"""Regressões dos pontos de entrada e do calendário UTC, sem chamadas AWS."""

from datetime import UTC, date, datetime
from unittest.mock import patch

import pytest

import lambda_function
from src.aws import cost_explorer
from src.operations import serverless


def test_handler_legado_encaminha_ao_coordenador():
    with patch.object(
        serverless, "lambda_handler", return_value={"statusCode": 409}
    ) as coordinator:
        assert lambda_function.lambda_handler({"recovery": {}}, None) == {
            "statusCode": 409
        }
        coordinator.assert_called_once_with({"recovery": {}}, None)


@pytest.mark.parametrize(
    "instant,end,start",
    [
        ("2026-12-31T23:59:59+00:00", "2026-12-31", "2026-12-30"),
        ("2027-01-01T00:00:00+00:00", "2027-01-01", "2026-12-31"),
        ("2028-03-01T00:00:00+00:00", "2028-03-01", "2028-02-29"),
    ],
)
def test_periodo_utc_independente_do_fuso_local(instant, end, start):
    with (
        patch.object(cost_explorer, "datetime", create=True) as clock,
        patch.object(cost_explorer.boto3, "client") as boto,
    ):
        clock.now.return_value = datetime.fromisoformat(instant)
        boto.return_value.get_cost_and_usage.return_value = {"ResultsByTime": []}
        cost_explorer.get_costs(period_days=1)
        clock.now.assert_called_once_with(UTC)
        assert boto.return_value.get_cost_and_usage.call_args.kwargs["TimePeriod"] == {
            "Start": start,
            "End": end,
        }


def test_periodo_explicito_preserva_dia_da_reserva():
    with patch.object(cost_explorer.boto3, "client") as boto:
        boto.return_value.get_cost_and_usage.return_value = {"ResultsByTime": []}
        cost_explorer.get_costs(period_days=30, end_date=date(2027, 1, 1))
        assert boto.return_value.get_cost_and_usage.call_args.kwargs["TimePeriod"] == {
            "Start": "2026-12-02",
            "End": "2027-01-01",
        }


def test_sqlite_consulta_dia_da_reserva_apos_meia_noite(tmp_path, costs_single_period):
    """O relógio da coleta pode avançar sem mudar a janela reservada."""
    from src.database.repository import _get_connection
    from src.operations import collection

    clock = datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC)
    with (
        patch.object(collection, "datetime") as mocked,
        patch.object(
            collection, "get_costs", return_value=costs_single_period
        ) as collect,
    ):
        mocked.now.return_value = clock

        def after_midnight(**kwargs):
            mocked.now.return_value = datetime(2027, 1, 1, tzinfo=UTC)
            return costs_single_period

        collect.side_effect = after_midnight
        path = tmp_path / "midnight.db"
        collection.collect_once(path)
        assert collect.call_args.kwargs["end_date"] == clock.date()
        with _get_connection(path) as conn:
            assert (
                conn.execute("SELECT job_key FROM collection_jobs").fetchone()[0]
                == "2026-12-31"
            )
