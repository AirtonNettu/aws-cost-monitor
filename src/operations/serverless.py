"""Coordena estados da guarda diária e publica um artefato privado idempotente."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import os
from uuid import UUID, uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from lambda_function import run_report as run_legacy
from src import config
from src.operations.budget import Budget, BudgetExceeded

logger = logging.getLogger("cost_monitor.lambda")
logger.setLevel(logging.INFO)
SDK_CONFIG = Config(
    connect_timeout=1,
    read_timeout=2,
    retries={"mode": "standard", "total_max_attempts": 1},
)
MAX_ATTEMPTS = 2


class RecoveryBlocked(Exception):
    """A guarda mudou ou os pré-requisitos de recuperação não foram atendidos."""


def _now():
    return datetime.now(timezone.utc)


def _code(error):
    return error.response.get("Error", {}).get("Code")


def inspect_guard(client, bucket, day):
    """Lê somente o pequeno registro operacional privado, nunca o relatório."""
    result = client.get_object(Bucket=bucket, Key=f"locks/{day}.json")
    stream = result["Body"]
    try:
        content = stream.read(8193)
    finally:
        stream.close()
    if len(content) > 8192:
        raise RecoveryBlocked("Guarda inválida.")
    guard = json.loads(content)
    if not isinstance(guard, dict) or set(guard) != {
        "state",
        "token",
        "scope",
        "attempts",
        "recover_after",
    }:
        raise RecoveryBlocked("Guarda inválida ou legada.")
    UUID(guard["token"])
    if (
        guard["state"] not in ("running", "failed", "succeeded")
        or type(guard["attempts"]) is not int
        or not 1 <= guard["attempts"] <= MAX_ATTEMPTS
        or len(guard["scope"]) != 64
    ):
        raise RecoveryBlocked("Guarda inválida ou legada.")
    expires = datetime.fromisoformat(guard["recover_after"])
    if expires.tzinfo is None or not isinstance(result["ETag"], str):
        raise RecoveryBlocked("Metadados incompletos.")
    return guard, result["ETag"]


def _write(client, bucket, key, guard, budget, **condition):
    budget.require(4)
    response = client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(guard, sort_keys=True).encode(),
        ContentType="application/json",
        **condition,
    )
    etag = response.get("ETag")
    if not isinstance(etag, str):
        raise RecoveryBlocked("Gravação sem confirmação do identificador da guarda.")
    return etag


def _report_exists(client, bucket, key, scope, budget):
    budget.require(12)
    listing = client.list_objects_v2(Bucket=bucket, Prefix=key, MaxKeys=1)
    if not any(item.get("Key") == key for item in listing.get("Contents", [])):
        return False
    budget.require(12)
    result = client.head_object(Bucket=bucket, Key=key)
    if result.get("Metadata", {}).get("scope-hash") != scope:
        raise RecoveryBlocked(
            "Relatório existente com escopo desconhecido ou diferente."
        )
    return True


def lambda_handler(event, context):
    """Executa uma tentativa; recuperação exige evento administrativo explícito."""
    bucket = os.getenv("S3_BUCKET_NAME")
    if not bucket:
        return _response(503, "CONFIGURATION_ERROR")
    now = _now()
    day = now.date().isoformat()
    key = f"locks/{day}.json"
    report = f"reports/{day}.html"
    budget = Budget(context)
    guard = None
    etag = None
    try:
        budget.require(18)
        days = int(os.getenv("COST_PERIOD_DAYS", "30"))
        granularity = os.getenv("COST_GRANULARITY", "DAILY").strip().upper()
        if not 1 <= days <= 366 or granularity not in ("DAILY", "MONTHLY"):
            return _response(503, "CONFIGURATION_ERROR")
        scope = hashlib.sha256(
            json.dumps(
                {
                    "days": days,
                    "tag": config.COST_TAG_KEY,
                    "metric": config.COST_METRIC,
                    "granularity": granularity,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        client = boto3.client("s3", config=SDK_CONFIG)
        recovery = event.get("recovery") if isinstance(event, dict) else None
        if recovery is not None:
            guard, etag = inspect_guard(client, bucket, day)
            if (
                not isinstance(recovery, dict)
                or (
                    recovery.get("confirm_stopped") is not True
                    or recovery.get("allow_paid_retry") is not True
                )
                or recovery.get("expected_token") != guard["token"]
                or recovery.get("expected_etag") != etag
                or guard["state"] == "succeeded"
                or guard["scope"] != scope
            ):
                raise RecoveryBlocked("Recuperação não autorizada para esta reserva.")
            if guard["state"] == "running" and now < datetime.fromisoformat(
                guard["recover_after"]
            ):
                raise RecoveryBlocked("Execução ainda pode estar ativa.")
            if _report_exists(client, bucket, report, scope, budget):
                guard["state"] = "succeeded"
                _write(client, bucket, key, guard, budget, IfMatch=etag)
                return _response(200, "succeeded")
            if guard["attempts"] >= MAX_ATTEMPTS:
                raise RecoveryBlocked("Limite de tentativas atingido.")
            guard = {
                **guard,
                "state": "running",
                "token": str(uuid4()),
                "attempts": guard["attempts"] + 1,
                "recover_after": (now + timedelta(seconds=120)).isoformat(),
            }
            etag = _write(client, bucket, key, guard, budget, IfMatch=etag)
        else:
            guard = {
                "state": "running",
                "token": str(uuid4()),
                "scope": scope,
                "attempts": 1,
                "recover_after": (now + timedelta(seconds=120)).isoformat(),
            }
            try:
                etag = _write(client, bucket, key, guard, budget, IfNoneMatch="*")
            except ClientError as error:
                if _code(error) in (
                    "PreconditionFailed",
                    "412",
                    "ConditionalRequestConflict",
                    "409",
                ):
                    return _response(200, "already_claimed")
                raise
        logger.info(
            json.dumps(
                {
                    "event": "collection_reserved",
                    "attempt": guard["attempts"],
                    "request_id": getattr(context, "aws_request_id", None),
                }
            )
        )
        if _report_exists(client, bucket, report, scope, budget):
            status = 200
        else:
            result = run_legacy(
                {},
                context,
                client=client,
                destination_key=report,
                put_options={"IfNoneMatch": "*", "Metadata": {"scope-hash": scope}},
                sdk_config=SDK_CONFIG,
                max_pages=5,
                before_call=lambda: budget.require(12),
            )
            status = result["statusCode"]
            if status == 200 and not _report_exists(
                client, bucket, report, scope, budget
            ):
                raise RuntimeError("Publicação não confirmada.")
        guard["state"] = "succeeded" if status == 200 else "failed"
        _write(client, bucket, key, guard, budget, IfMatch=etag)
        return _response(status, guard["state"])
    except RecoveryBlocked:
        return _response(409, "RECOVERY_BLOCKED")
    except Exception as error:
        if isinstance(error, ClientError) and _code(error) in (
            "PreconditionFailed",
            "412",
            "ConditionalRequestConflict",
            "409",
        ):
            return _response(409, "RECOVERY_BLOCKED")
        # Sem tempo ou com resposta ambígua, manter reserva; nunca liberar por exclusão.
        if etag is not None and guard is not None:
            try:
                guard["state"] = "failed"
                _write(client, bucket, key, guard, budget, IfMatch=etag)
            except Exception:
                pass
        return _response(
            503,
            "BUDGET_EXHAUSTED"
            if isinstance(error, BudgetExceeded)
            else "COLLECTION_FAILED",
        )


def _response(status, code):
    logger.info(
        json.dumps({"event": "collection_result", "status": status, "code": code})
    )
    return {"statusCode": status, "body": json.dumps({"status": code})}
