"""Handler para AWS Lambda do AWS Cost Monitor.

Executado automaticamente pelo Amazon EventBridge (ex: 1x ao dia).
Coleta os custos no AWS Cost Explorer, calcula métricas de FinOps,
gera o relatório HTML interativo com Chart.js e publica como index.html
em um bucket S3 configurado como Static Website.
"""

import json
import logging
import os
import sys

# Garante que a raiz do projeto esteja no sys.path para os imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import boto3
from botocore.config import Config
from src import config
from src.analysis.cost_analyzer import analyze_costs, compare_periods
from src.analysis.finops_rules import generate_alerts
from src.aws.cost_explorer import CostExplorerError, get_costs
from src.reports.report_generator import build_report_html


def lambda_handler(event, context):
    """Ponto de entrada da função AWS Lambda."""
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    if not bucket_name:
        error_msg = "Variável de ambiente S3_BUCKET_NAME não configurada na Lambda."
        logging.getLogger(__name__).error(json.dumps({"event": "configuration_error"}))
        return {"statusCode": 500, "body": json.dumps({"error": error_msg})}

    days = int(os.environ.get("COST_PERIOD_DAYS", "30"))
    raw_granularity = os.environ.get("COST_GRANULARITY", "DAILY").strip().upper()
    granularity = raw_granularity if raw_granularity in {"DAILY", "MONTHLY", "HOURLY"} else "DAILY"

    logging.getLogger(__name__).info(json.dumps({"event": "collection_started"}))

    # 1. Coleta ------------------------------------------------------------
    try:
        costs = get_costs(period_days=days, granularity=granularity)
    except CostExplorerError as err:
        logging.getLogger(__name__).error(json.dumps({"event": "collection_failed"}))
        return {"statusCode": 500, "body": json.dumps({"error": "COLLECTION_FAILED"})}

    if not costs:
        print("[AVISO] Nenhum custo encontrado para o período.")
        return {"statusCode": 200, "body": json.dumps({"message": "Sem custos para o período."})}

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

    # 4. Upload para o S3 Website (index.html) ------------------------------
    s3_client = boto3.client("s3", config=Config(connect_timeout=2, read_timeout=4, retries={"mode": "standard", "total_max_attempts": 2}))
    destination_key = os.environ.get("S3_OBJECT_KEY", "index.html")

    logging.getLogger(__name__).info(json.dumps({"event": "report_upload_started"}))
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=destination_key,
            Body=html_content.encode("utf-8"),
            ContentType="text/html; charset=utf-8",
        )
        logging.getLogger(__name__).info(json.dumps({"event": "report_upload_succeeded"}))
    except Exception as exc:
        logging.getLogger(__name__).error(json.dumps({"event": "report_upload_failed"}))
        return {"statusCode": 500, "body": json.dumps({"error": "UPLOAD_FAILED"})}

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Dashboard atualizada com sucesso no S3!",
            "bucket": bucket_name,
            "key": destination_key,
            "total_cost": analysis["total_cost"],
            "alerts_count": len(alerts),
        }),
    }
