"""Fixtures com dados fictícios (sem dependência da AWS real)."""

import pytest


def _group(service, amount):
    """Monta um grupo no formato retornado pelo Cost Explorer."""
    return {
        "Keys": [service],
        "Metrics": {"UnblendedCost": {"Amount": str(amount), "Unit": "USD"}},
    }


def _period(start, end, groups, estimated=False):
    return {"start": start, "end": end, "estimated": estimated, "groups": groups}


@pytest.fixture
def costs_single_period():
    """Um período com três serviços de custo positivo."""
    return [
        _period(
            "2026-08-01",
            "2026-09-01",
            [
                _group("Amazon S3", 10.0),
                _group("Amazon EC2", 30.0),
                _group("AWS Lambda", 10.0),
            ],
        )
    ]


@pytest.fixture
def costs_two_periods():
    """Dois períodos, usados para comparação."""
    return [
        _period("2026-07-01", "2026-08-01", [_group("Amazon S3", 100.0)]),
        _period("2026-08-01", "2026-09-01", [_group("Amazon S3", 150.0)]),
    ]


@pytest.fixture
def costs_previous_zero():
    """Período anterior com custo zero (gatilho de divisão por zero)."""
    return [
        _period("2026-07-01", "2026-08-01", [_group("Amazon S3", 0.0)]),
        _period("2026-08-01", "2026-09-01", [_group("Amazon S3", 50.0)]),
    ]


@pytest.fixture
def costs_empty():
    """Período sem nenhum grupo."""
    return [_period("2026-08-01", "2026-09-01", [])]


@pytest.fixture
def costs_with_negative():
    """Período com um crédito/ajuste negativo e um serviço positivo."""
    return [
        _period(
            "2026-08-01",
            "2026-09-01",
            [
                _group("Amazon EC2", 40.0),
                _group("Refund", -10.0),
            ],
        )
    ]
