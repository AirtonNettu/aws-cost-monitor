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


def get_costs(period_days=None, granularity=None, tag_key=None):
    """Consulta o AWS Cost Explorer e retorna os custos agrupados por serviço ou tag.

    Parâmetros
    ----------
    period_days : int | None
        Janela de dias a consultar. Usa ``config.COST_PERIOD_DAYS`` se None.
    granularity : str | None
        Granularidade da consulta ("DAILY" ou "MONTHLY"). Usa
        ``config.COST_GRANULARITY`` se None.
    tag_key : str | None
        Chave da Cost Allocation Tag da AWS (ex: "Environment", "Project").
        Se fornecido, agrupa custos pelos valores dessa tag em vez de serviços.
        Usa ``config.COST_TAG_KEY`` se None.

    Retorno
    -------
    list[dict]
        Um item por período, com as chaves ``start``, ``end``, ``estimated``
        e ``groups`` (a lista de serviços ou tags retornada pela AWS).

    Levanta
    -------
    CostExplorerError
        Em caso de credenciais ausentes/incompletas, permissão insuficiente
        ou qualquer falha na chamada ao Cost Explorer. O erro original é
        preservado na cadeia de exceções (``raise ... from``).
    """
    if period_days is None:
        period_days = config.COST_PERIOD_DAYS
    granularity = (granularity or config.COST_GRANULARITY).strip().upper()
    if granularity not in {"DAILY", "MONTHLY", "HOURLY"}:
        granularity = "DAILY"
    if tag_key is None:
        tag_key = config.COST_TAG_KEY

    end_date = date.today()
    start_date = end_date - timedelta(days=period_days)

    results_by_time = []
    next_page_token = None

    if tag_key:
        group_by = [{"Type": "TAG", "Key": tag_key}]
    else:
        group_by = [{"Type": "DIMENSION", "Key": "SERVICE"}]

    try:
        client = boto3.client("ce", region_name=config.AWS_REGION)
        while True:
            params = {
                "TimePeriod": {
                    "Start": start_date.isoformat(),
                    "End": end_date.isoformat(),
                },
                "Granularity": granularity,
                "Metrics": [config.COST_METRIC],
                "GroupBy": group_by,
            }
            if next_page_token:
                params["NextPageToken"] = next_page_token

            response = client.get_cost_and_usage(**params)
            results_by_time.extend(response.get("ResultsByTime", []))

            next_page_token = response.get("NextPageToken")
            if not next_page_token:
                break
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

    # Consolida períodos e seus grupos preservando a ordem cronológica
    periods_map = {}
    for period in results_by_time:
        key = (period["TimePeriod"]["Start"], period["TimePeriod"]["End"])

        # Se agrupado por tag, normaliza a chave 'TagKey$Valor' -> 'TagKey: Valor' ou 'Untagged'
        normalized_groups = []
        for g in period.get("Groups", []):
            raw_key = g["Keys"][0] if g.get("Keys") else "Desconhecido"
            if tag_key and "$" in raw_key:
                t_name, t_val = raw_key.split("$", 1)
                clean_name = f"{t_name}: {t_val}" if t_val.strip() else f"{t_name}: Untagged"
            else:
                clean_name = raw_key
            normalized_groups.append({
                "Keys": [clean_name],
                "Metrics": g.get("Metrics", {}),
            })

        if key not in periods_map:
            periods_map[key] = {
                "start": key[0],
                "end": key[1],
                "estimated": period.get("Estimated", False),
                "groups": normalized_groups,
            }
        else:
            periods_map[key]["groups"].extend(normalized_groups)
            if period.get("Estimated"):
                periods_map[key]["estimated"] = True

    return list(periods_map.values())


if __name__ == "__main__":
    try:
        for cost in get_costs():
            print(cost)
    except CostExplorerError as error:
        print(f"Erro: {error}")
