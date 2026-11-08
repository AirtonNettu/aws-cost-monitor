"""S3 em memória reproduz CAS, escrita ambígua e recuperação sem conta AWS."""

from datetime import timedelta
import hashlib
import io
import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError, ReadTimeoutError
from src.operations import serverless


def failure(code):
    return ClientError({"Error": {"Code": code}}, "SyntheticOperation")


class S3Memory:
    def __init__(self):
        self.objects = {}
        self.ambiguous_report = False
        self.report_writes = 0

    def put_object(self, **kwargs):
        key = kwargs["Key"]
        old = self.objects.get(key)
        if kwargs.get("IfNoneMatch") == "*" and old:
            raise failure("PreconditionFailed")
        if "IfMatch" in kwargs and (not old or kwargs["IfMatch"] != old["ETag"]):
            raise failure("PreconditionFailed")
        body = kwargs["Body"]
        etag = '"' + hashlib.sha256(body).hexdigest() + '"'
        self.objects[key] = {
            "Body": body,
            "ETag": etag,
            "Metadata": kwargs.get("Metadata", {}),
        }
        if key.startswith("reports/"):
            self.report_writes += 1
            if self.ambiguous_report:
                self.ambiguous_report = False
                raise ReadTimeoutError(endpoint_url="https://s3.example.test")
        return {"ETag": etag}

    def list_objects_v2(self, **kwargs):
        assert kwargs["MaxKeys"] == 1
        return {
            "Contents": [
                {"Key": key}
                for key in sorted(self.objects)
                if key.startswith(kwargs["Prefix"])
            ][:1]
        }

    def get_object(self, **kwargs):
        obj = self.objects[kwargs["Key"]]
        return {**obj, "Body": io.BytesIO(obj["Body"])}

    def head_object(self, **kwargs):
        if kwargs["Key"] not in self.objects:
            raise failure("404")
        return self.objects[kwargs["Key"]]


def recovery(s3):
    guard, etag = serverless.inspect_guard(
        s3, "synthetic", serverless._now().date().isoformat()
    )
    return {
        "recovery": {
            "expected_token": guard["token"],
            "expected_etag": etag,
            "confirm_stopped": True,
            "allow_paid_retry": True,
        }
    }


@pytest.fixture
def storage(monkeypatch):
    monkeypatch.setenv("S3_BUCKET_NAME", "synthetic")
    return S3Memory()


def test_resposta_upload_perdida_reconcilia_sem_recoletar(storage, costs_single_period):
    storage.ambiguous_report = True
    with (
        patch.object(serverless.boto3, "client", return_value=storage),
        patch("lambda_function.get_costs", return_value=costs_single_period) as aws,
    ):
        assert serverless.lambda_handler({}, None)["statusCode"] == 500
        assert serverless.lambda_handler(recovery(storage), None)["statusCode"] == 200
        assert serverless.lambda_handler({}, None)["statusCode"] == 200
        assert aws.call_count == 1
        assert storage.report_writes == 1
    guard, _ = serverless.inspect_guard(
        storage, "synthetic", serverless._now().date().isoformat()
    )
    assert guard["state"] == "succeeded"


def test_recuperacao_etag_obsoleto_e_teto_duas_tentativas(storage):
    with (
        patch.object(serverless.boto3, "client", return_value=storage),
        patch.object(serverless, "run_legacy", return_value={"statusCode": 500}) as aws,
    ):
        serverless.lambda_handler({}, None)
        stale = recovery(storage)
        assert serverless.lambda_handler(stale, None)["statusCode"] == 500
        assert serverless.lambda_handler(stale, None)["statusCode"] == 409
        assert serverless.lambda_handler(recovery(storage), None)["statusCode"] == 409
        assert aws.call_count == 2


def test_running_nao_expirado_bloqueia_recuperacao(storage):
    with (
        patch.object(serverless.boto3, "client", return_value=storage),
        patch.object(serverless, "run_legacy", side_effect=RuntimeError("segredo")),
    ):
        serverless.lambda_handler({}, None)
    day = serverless._now().date().isoformat()
    guard, etag = serverless.inspect_guard(storage, "synthetic", day)
    guard["state"] = "running"
    storage.put_object(
        Key=f"locks/{day}.json", Body=json.dumps(guard).encode(), IfMatch=etag
    )
    with (
        patch.object(serverless.boto3, "client", return_value=storage),
        patch.object(serverless, "run_legacy") as aws,
    ):
        assert serverless.lambda_handler(recovery(storage), None)["statusCode"] == 409
        aws.assert_not_called()


def test_sem_orcamento_nao_inicia_sdk(storage):
    context = MagicMock()
    context.get_remaining_time_in_millis.return_value = 1000
    with patch.object(serverless.boto3, "client") as sdk:
        response = serverless.lambda_handler({}, context)
        assert response["statusCode"] == 503
        assert "BUDGET_EXHAUSTED" in response["body"]
        sdk.assert_not_called()


def test_paginacao_para_antes_de_consumir_reserva_de_finalizacao(storage):
    context = MagicMock(aws_request_id="synthetic")
    context.get_remaining_time_in_millis.side_effect = [
        60000,
        60000,
        60000,
        60000,
        11000,
        11000,
    ]
    ce = MagicMock()
    ce.get_cost_and_usage.return_value = {"ResultsByTime": [], "NextPageToken": "next"}

    def sdk(service, **kwargs):
        assert kwargs["config"].retries["total_max_attempts"] == 1
        return storage if service == "s3" else ce

    with patch.object(serverless.boto3, "client", side_effect=sdk):
        response = serverless.lambda_handler({}, context)
        assert "BUDGET_EXHAUSTED" in response["body"]
        assert ce.get_cost_and_usage.call_count == 1
        assert storage.report_writes == 0


def test_running_expirado_exige_confirmacao_e_preserva_exclusao(storage):
    with (
        patch.object(serverless.boto3, "client", return_value=storage),
        patch.object(serverless, "run_legacy", return_value={"statusCode": 500}),
    ):
        serverless.lambda_handler({}, None)
    day = serverless._now().date().isoformat()
    guard, etag = serverless.inspect_guard(storage, "synthetic", day)
    guard.update(
        state="running",
        recover_after=(serverless._now() - timedelta(seconds=1)).isoformat(),
    )
    storage.put_object(
        Key=f"locks/{day}.json", Body=json.dumps(guard).encode(), IfMatch=etag
    )
    event = recovery(storage)
    with (
        patch.object(serverless.boto3, "client", return_value=storage),
        patch.object(serverless, "run_legacy", return_value={"statusCode": 500}) as aws,
    ):
        assert serverless.lambda_handler(event, None)["statusCode"] == 500
        assert serverless.lambda_handler(event, None)["statusCode"] == 409
        assert aws.call_count == 1


def test_segunda_tentativa_com_upload_ambiguo_so_reconcilia(
    storage, costs_single_period
):
    with (
        patch.object(serverless.boto3, "client", return_value=storage),
        patch.object(serverless, "run_legacy", return_value={"statusCode": 500}),
    ):
        serverless.lambda_handler({}, None)
    storage.ambiguous_report = True
    with (
        patch.object(serverless.boto3, "client", return_value=storage),
        patch("lambda_function.get_costs", return_value=costs_single_period) as aws,
    ):
        assert serverless.lambda_handler(recovery(storage), None)["statusCode"] == 500
        assert serverless.lambda_handler(recovery(storage), None)["statusCode"] == 200
        assert aws.call_count == 1
        assert storage.report_writes == 1


def test_erro_de_rede_da_guarda_nao_expoe_detalhes():
    with (
        patch.dict("os.environ", {"S3_BUCKET_NAME": "synthetic"}),
        patch.object(serverless.boto3, "client") as boto,
        patch.object(serverless, "run_legacy") as aws,
    ):
        boto.return_value.put_object.side_effect = RuntimeError("DADOS_SENSIVEIS")
        response = serverless.lambda_handler({}, None)
        assert response["statusCode"] == 503
        assert "DADOS_SENSIVEIS" not in response["body"]
        aws.assert_not_called()


def test_teto_cinco_paginas_nao_publica_parcial(storage):
    ce = MagicMock()
    ce.get_cost_and_usage.side_effect = [
        {"ResultsByTime": [], "NextPageToken": f"page-{i}"} for i in range(5)
    ]
    with patch.object(
        serverless.boto3,
        "client",
        side_effect=lambda service, **kw: storage if service == "s3" else ce,
    ):
        response = serverless.lambda_handler({}, None)
        assert response["statusCode"] == 500
        assert ce.get_cost_and_usage.call_count == 5
        assert storage.report_writes == 0


def test_cas_concorrente_nao_transfere_nem_finaliza_guarda_alheia(storage):
    with (
        patch.object(serverless.boto3, "client", return_value=storage),
        patch.object(serverless, "run_legacy", return_value={"statusCode": 500}),
    ):
        serverless.lambda_handler({}, None)
    event = recovery(storage)
    original = storage.put_object

    def racing_write(**kwargs):
        if "IfMatch" in kwargs:
            raise failure("PreconditionFailed")
        return original(**kwargs)

    with (
        patch.object(serverless.boto3, "client", return_value=storage),
        patch.object(storage, "put_object", side_effect=racing_write),
        patch.object(serverless, "run_legacy") as aws,
    ):
        assert serverless.lambda_handler(event, None)["statusCode"] == 409
        aws.assert_not_called()


def test_chave_ausente_nao_depende_de_head_404(storage, costs_single_period):
    """Ausência deve ser consultada com prefixo explícito, não inferida de 403."""
    original = storage.head_object

    def private_head(**kwargs):
        if kwargs["Key"] not in storage.objects:
            raise failure("403")
        return original(**kwargs)

    with (
        patch.object(storage, "head_object", side_effect=private_head),
        patch.object(serverless.boto3, "client", return_value=storage),
        patch("lambda_function.get_costs", return_value=costs_single_period) as aws,
    ):
        assert serverless.lambda_handler({}, None)["statusCode"] == 200
        assert aws.call_count == 1


def test_coleta_vazia_nao_confirma_publicacao_inexistente(storage):
    with (
        patch.object(serverless.boto3, "client", return_value=storage),
        patch("lambda_function.get_costs", return_value=[]),
    ):
        assert serverless.lambda_handler({}, None)["statusCode"] == 503
    guard, _ = serverless.inspect_guard(
        storage, "synthetic", serverless._now().date().isoformat()
    )
    assert guard["state"] == "failed"
    assert storage.report_writes == 0
