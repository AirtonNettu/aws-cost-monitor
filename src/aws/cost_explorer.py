"""Coleta de custos no AWS Cost Explorer via boto3.

Esta é a única camada que fala com a AWS. Não realiza cálculos de FinOps:
apenas consulta e organiza a resposta bruta para a camada de análise.

As credenciais são obtidas pelo boto3 a partir da configuração local
(AWS CLI / variáveis de ambiente). Nenhuma chave é lida ou guardada aqui.
"""

from datetime import date, timedelta

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
)

from src import config


class CostExplorerError(Exception):
    """Erro de alto nível na coleta de custos, com mensagem amigável."""


def get_costs(period_days=None):
    """Consulta o AWS Cost Explorer e retorna os custos agrupados por serviço.

    Parâmetros
    ----------
    period_days : int | None
        Janela de dias a consultar. Usa ``config.COST_PERIOD_DAYS`` se None.

    Retorno
    -------
    list[dict]
        Um item por período, com as chaves ``start``, ``end``, ``estimated``
        e ``groups`` (a lista de serviços retornada pela AWS).

    Levanta
    -------
    CostExplorerError
        Em caso de credenciais ausentes/incompletas, permissão insuficiente
        ou qualquer falha na chamada ao Cost Explorer. O erro original é
        preservado na cadeia de exceções (``raise ... from``).
    """
    if period_days is None:
        period_days = config.COST_PERIOD_DAYS

    end_date = date.today()
    start_date = end_date - timedelta(days=period_days)

    try:
        client = boto3.client("ce", region_name=config.AWS_REGION)
        response = client.get_cost_and_usage(
            TimePeriod={
                "Start": start_date.isoformat(),
                "End": end_date.isoformat(),
            },
            Granularity=config.COST_GRANULARITY,
            Metrics=[config.COST_METRIC],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
    except (NoCredentialsError, PartialCredentialsError) as exc:
        raise CostExplorerError(
            "Credenciais da AWS não encontradas ou incompletas. "
            "Configure com 'aws configure' ou defina as variáveis de ambiente."
        ) from exc
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Desconhecido")
        if code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}:
            raise CostExplorerError(
                "Permissão insuficiente para consultar o Cost Explorer. "
                "A identidade AWS precisa da permissão 'ce:GetCostAndUsage'."
            ) from exc
        raise CostExplorerError(
            f"O AWS Cost Explorer retornou um erro ({code}): {exc}"
        ) from exc
    except BotoCoreError as exc:
        raise CostExplorerError(
            f"Falha de comunicação com a AWS: {exc}"
        ) from exc

    results = []
    for period in response.get("ResultsByTime", []):
        results.append(
            {
                "start": period["TimePeriod"]["Start"],
                "end": period["TimePeriod"]["End"],
                "estimated": period.get("Estimated", False),
                "groups": period.get("Groups", []),
            }
        )

    return results


if __name__ == "__main__":
    try:
        for cost in get_costs():
            print(cost)
    except CostExplorerError as error:
        print(f"Erro: {error}")
