"""Proteção diária no S3 antes da coleta serverless legada."""
from datetime import datetime, timezone
import json
import logging
import os

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from lambda_function import lambda_handler as run_legacy

logger = logging.getLogger('cost_monitor.lambda')


def lambda_handler(event, context):
    """Reserva uma execução diária; uma reserva com falha exige ação do operador."""
    bucket = os.getenv('S3_BUCKET_NAME')
    if not bucket:
        return {'statusCode': 503, 'body': json.dumps({'error': 'CONFIGURATION_ERROR'})}
    day = datetime.now(timezone.utc).date().isoformat()
    client = boto3.client('s3', config=Config(connect_timeout=2, read_timeout=4,
        retries={'mode': 'standard', 'total_max_attempts': 2}))
    try:
        client.put_object(Bucket=bucket, Key=f'locks/{day}.json', Body=b'{"state":"claimed"}',
                          ContentType='application/json', IfNoneMatch='*')
    except ClientError as error:
        if error.response.get('Error', {}).get('Code') in ('PreconditionFailed', '412', 'ConditionalRequestConflict'):
            logger.info(json.dumps({'event': 'collection_skipped', 'reason': 'daily_guard'}))
            return {'statusCode': 200, 'body': json.dumps({'status': 'already_claimed'})}
        logger.error(json.dumps({'event': 'collection_failed', 'code': 'GUARD_FAILED'}))
        return {'statusCode': 503, 'body': json.dumps({'error': 'GUARD_FAILED'})}
    try:
        result = run_legacy(event, context)
        status = result['statusCode']
    except Exception:
        status = 500
    logger.info(json.dumps({'event': 'collection_finished', 'status': status,
        'request_id': getattr(context, 'aws_request_id', None)}))
    return {'statusCode': status, 'body': json.dumps({'status': 'succeeded' if status == 200 else 'failed'})}
