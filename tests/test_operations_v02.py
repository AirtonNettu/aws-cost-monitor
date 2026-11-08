"""Regressões operacionais com serviços externos simulados."""
from unittest.mock import patch
import pytest
from src.analysis.cost_analyzer import analyze_costs
from src.reports.report_generator import build_report_html


def test_html_nao_fecha_script_com_nome_externo(costs_single_period):
    malicious = '</script><img src=x onerror=alert(1)>'
    costs_single_period[0]['groups'][0]['Keys'][0] = malicious
    output = build_report_html(costs_single_period, analyze_costs(costs_single_period), None)
    assert '</script><img' not in output
    assert '\\u003c/script' in output


def test_sdk_com_timeout_e_retenta_limitada():
    from src.aws.cost_explorer import get_costs
    with patch('src.aws.cost_explorer.boto3.client') as client:
        client.return_value.get_cost_and_usage.return_value = {'ResultsByTime': []}
        get_costs()
        config = client.call_args.kwargs['config']
        assert config.connect_timeout == 2
        assert config.read_timeout == 4
        assert config.retries['total_max_attempts'] == 2


def test_coleta_diaria_idempotente(tmp_path, costs_single_period):
    from src.operations.collection import collect_once
    with patch('src.operations.collection.get_costs', return_value=costs_single_period) as collect:
        first = collect_once(tmp_path / 'a.db')
        second = collect_once(tmp_path / 'a.db')
        assert first == second
        assert collect.call_count == 1


def test_falha_coleta_registrada_sem_retry_cego(tmp_path):
    from src.operations.collection import collect_once, CollectionBlocked
    from src.aws.cost_explorer import CostExplorerError
    with patch('src.operations.collection.get_costs', side_effect=CostExplorerError('privado')) as collect:
        with pytest.raises(CostExplorerError):
            collect_once(tmp_path / 'a.db')
        with pytest.raises(CollectionBlocked):
            collect_once(tmp_path / 'a.db')
        assert collect.call_count == 1


def test_paginacao_repetida_falha_sem_resultado_parcial():
    from src.aws.cost_explorer import get_costs, CostExplorerError
    with patch('src.aws.cost_explorer.boto3.client') as client:
        client.return_value.get_cost_and_usage.return_value = {'ResultsByTime': [], 'NextPageToken': 'repetido'}
        with pytest.raises(CostExplorerError, match='paginação'):
            get_costs()
        assert client.return_value.get_cost_and_usage.call_count == 2


def test_guard_serverless_impede_segunda_coleta():
    from botocore.exceptions import ClientError
    from src.operations.serverless import lambda_handler
    with patch.dict('os.environ', {'S3_BUCKET_NAME': 'bucket-sintetico'}), patch('src.operations.serverless.boto3.client') as boto, patch('src.operations.serverless.run_legacy') as legacy:
        boto.return_value.put_object.side_effect = ClientError({'Error': {'Code': 'PreconditionFailed'}}, 'PutObject')
        assert lambda_handler({}, None)['statusCode'] == 200
        legacy.assert_not_called()
