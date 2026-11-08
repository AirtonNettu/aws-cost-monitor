"""Compatibilidade de importação e geração interna do relatório privado.

Ambos os handlers públicos usam o coordenador diário. ``run_report`` é um
helper interno; não deve ser configurado como handler da infraestrutura.
"""

import json
import logging
import os
import sys

# Garante que a raiz do projeto esteja no sys.path para os imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import boto3
from botocore.config import Config

from src.analysis.cost_analyzer import analyze_costs, compare_periods
from src.analysis.finops_rules import generate_alerts
from src.aws.cost_explorer import CostExplorerError, get_costs
from src.reports.report_generator import build_report_html


def lambda_handler(event, context):
    """Encaminha configurações antigas ao mesmo coordenador seguro da stack."""
    from src.operations.serverless import lambda_handler as coordinated_handler

    return coordinated_handler(event, context)


def run_report(
    event,
    context,
    *,
    client=None,
    destination_key=None,
    put_options=None,
    sdk_config=None,
    before_call=None,
    max_pages=20,
    end_date=None,
):
    """Gera o relatório após a reserva; uso interno do coordenador diário."""
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    if not bucket_name:
        error_msg = "Variável de ambiente S3_BUCKET_NAME não configurada na Lambda."
        logging.getLogger(__name__).error(json.dumps({"event": "configuration_error"}))
        return {"statusCode": 500, "body": json.dumps({"error": error_msg})}

    days = int(os.environ.get("COST_PERIOD_DAYS", "30"))
    raw_granularity = os.environ.get("COST_GRANULARITY", "DAILY").strip().upper()
    granularity = (
        raw_granularity
        if raw_granularity in {"DAILY", "MONTHLY", "HOURLY"}
        else "DAILY"
    )

    logging.getLogger(__name__).info(json.dumps({"event": "collection_started"}))

    # 1. Coleta ------------------------------------------------------------
    try:
        options = {}
        if sdk_config is not None:
            options = {
                "sdk_config": sdk_config,
                "before_page": before_call,
                "max_pages": max_pages,
            }
        if end_date is not None:
            options["end_date"] = end_date
        costs = get_costs(period_days=days, granularity=granularity, **options)
    except CostExplorerError:
        logging.getLogger(__name__).error(json.dumps({"event": "collection_failed"}))
        return {"statusCode": 500, "body": json.dumps({"error": "COLLECTION_FAILED"})}

    if not costs:
        print("[AVISO] Nenhum custo encontrado para o período.")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Sem custos para o período."}),
        }

    # 2. Análise determinística de FinOps -----------------------------------
    analysis = analyze_costs(costs)
    comparison = compare_periods(costs)
    alerts = generate_alerts(analysis, comparison)

    # 3. Geração do relatório HTML standalone ------------------------------
    html_content = build_report_html(
        costs=costs,
        analysis=analysis,
        comparison=comparison,
        ai_interpretation=None,
        ai_error="IA não habilitada nesta execução serverless.",
        alerts=alerts,
    )

    # 4. Upload privado para o S3 ------------------------------
    s3_client = client or boto3.client(
        "s3",
        config=sdk_config
        or Config(
            connect_timeout=2,
            read_timeout=4,
            retries={"mode": "standard", "total_max_attempts": 2},
        ),
    )
    destination_key = destination_key or os.environ.get("S3_OBJECT_KEY", "index.html")

    logging.getLogger(__name__).info(json.dumps({"event": "report_upload_started"}))
    if before_call is not None:
        before_call()
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=destination_key,
            Body=html_content.encode("utf-8"),
            ContentType="text/html; charset=utf-8",
            **(put_options or {}),
        )
        logging.getLogger(__name__).info(
            json.dumps({"event": "report_upload_succeeded"})
        )
    except Exception:
        logging.getLogger(__name__).error(json.dumps({"event": "report_upload_failed"}))
        return {"statusCode": 500, "body": json.dumps({"error": "UPLOAD_FAILED"})}

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Dashboard atualizada com sucesso no S3!",
                "bucket": bucket_name,
                "key": destination_key,
                "total_cost": analysis["total_cost"],
                "alerts_count": len(alerts),
            }
        ),
    }
