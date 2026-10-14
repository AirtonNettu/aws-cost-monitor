"""Testes para o módulo cost_explorer com mocks do boto3."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from src.aws.cost_explorer import CostExplorerError, get_costs


@patch("src.aws.cost_explorer.boto3.client")
def test_get_costs_sucesso(mock_boto_client):
    mock_ce = MagicMock()
    mock_boto_client.return_value = mock_ce
    mock_ce.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-09-01", "End": "2026-10-01"},
                "Estimated": False,
                "Groups": [
                    {
                        "Keys": ["Amazon S3"],
                        "Metrics": {"UnblendedCost": {"Amount": "15.5", "Unit": "USD"}},
                    }
                ],
            }
        ]
    }

    results = get_costs(period_days=30, granularity="MONTHLY")
    assert len(results) == 1
    assert results[0]["start"] == "2026-09-01"
    assert results[0]["end"] == "2026-10-01"
    assert len(results[0]["groups"]) == 1
    assert results[0]["groups"][0]["Keys"] == ["Amazon S3"]


@patch("src.aws.cost_explorer.boto3.client")
def test_get_costs_com_paginacao(mock_boto_client):
    mock_ce = MagicMock()
    mock_boto_client.return_value = mock_ce

    # Duas páginas: a primeira retorna NextPageToken, a segunda finaliza
    page_1 = {
        "NextPageToken": "token123",
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-10-01", "End": "2026-10-02"},
                "Groups": [{"Keys": ["Amazon S3"], "Metrics": {"UnblendedCost": {"Amount": "5.0"}}}],
            }
        ],
    }
    page_2 = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-10-01", "End": "2026-10-02"},
                "Groups": [{"Keys": ["Amazon EC2"], "Metrics": {"UnblendedCost": {"Amount": "10.0"}}}],
            }
        ],
    }
    mock_ce.get_cost_and_usage.side_effect = [page_1, page_2]

    results = get_costs(period_days=1, granularity="DAILY")
    assert len(results) == 1
    # Ambos os grupos devem ter sido consolidados no mesmo período
    assert len(results[0]["groups"]) == 2
    keys = [g["Keys"][0] for g in results[0]["groups"]]
    assert "Amazon S3" in keys
    assert "Amazon EC2" in keys


@patch("src.aws.cost_explorer.boto3.client")
def test_get_costs_sem_credenciais(mock_boto_client):
    mock_ce = MagicMock()
    mock_boto_client.return_value = mock_ce
    mock_ce.get_cost_and_usage.side_effect = NoCredentialsError()

    with pytest.raises(CostExplorerError, match="Credenciais da AWS não encontradas"):
        get_costs()


@patch("src.aws.cost_explorer.boto3.client")
def test_get_costs_acesso_negado(mock_boto_client):
    mock_ce = MagicMock()
    mock_boto_client.return_value = mock_ce
    mock_ce.get_cost_and_usage.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
        "GetCostAndUsage",
    )

    with pytest.raises(CostExplorerError, match="Permissão insuficiente"):
        get_costs()


@patch("src.aws.cost_explorer.boto3.client")
def test_get_costs_com_tag_key(mock_boto_client):
    mock_ce = MagicMock()
    mock_boto_client.return_value = mock_ce
    mock_ce.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2026-10-01", "End": "2026-10-02"},
                "Groups": [
                    {
                        "Keys": ["Environment$prod"],
                        "Metrics": {"UnblendedCost": {"Amount": "25.0", "Unit": "USD"}},
                    },
                    {
                        "Keys": ["Environment$"],
                        "Metrics": {"UnblendedCost": {"Amount": "10.0", "Unit": "USD"}},
                    },
                ],
            }
        ]
    }

    results = get_costs(period_days=1, tag_key="Environment")
    assert len(results) == 1
    groups = results[0]["groups"]
    assert len(groups) == 2
    keys = [g["Keys"][0] for g in groups]
    assert "Environment: prod" in keys
    assert "Environment: Untagged" in keys

