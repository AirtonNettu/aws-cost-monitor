"""Testes unitários para o handler AWS Lambda (lambda_function.py)."""

from unittest.mock import MagicMock, patch

from lambda_function import lambda_handler


def test_lambda_handler_sem_bucket(monkeypatch):
    monkeypatch.delenv("S3_BUCKET_NAME", raising=False)
    resp = lambda_handler({}, {})
    assert resp["statusCode"] == 500
    assert "S3_BUCKET_NAME" in resp["body"]


@patch("lambda_function.boto3.client")
@patch("lambda_function.get_costs")
def test_lambda_handler_sucesso(mock_get_costs, mock_boto_client, costs_single_period, monkeypatch):
    monkeypatch.setenv("S3_BUCKET_NAME", "meu-bucket-teste")
    mock_get_costs.return_value = costs_single_period

    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    resp = lambda_handler({}, {})
    assert resp["statusCode"] == 200
    mock_s3.put_object.assert_called_once()
    kwargs = mock_s3.put_object.call_args.kwargs
    assert kwargs["Bucket"] == "meu-bucket-teste"
    assert kwargs["Key"] == "index.html"
    assert kwargs["ContentType"] == "text/html; charset=utf-8"
    assert b"AWS Cost Monitor" in kwargs["Body"]
