"""Camada de interpretação por IA (Llama local).

Princípio: Python calcula, IA interpreta.
Este módulo NÃO calcula nenhum valor financeiro. Ele recebe os números já
calculados deterministicamente pelo analyzer, monta um prompt com esses dados
e pede ao modelo apenas uma leitura/interpretação textual.

O cliente é propositalmente simples e desacoplado: fala com um servidor Llama
local compatível com a API do Ollama (POST /api/generate). Trocar o provedor
(OpenAI, Claude, Gemini, Bedrock) significa substituir este arquivo, sem tocar
na lógica de cálculo.
"""

import json

import requests

from src import config


class LlamaUnavailableError(Exception):
    """O servidor Llama não está acessível ou falhou ao responder."""


def _build_prompt(analysis, comparison):
    """Monta o prompt de interpretação a partir dos dados já calculados.

    Os valores financeiros são injetados prontos. O modelo é instruído a
    interpretar, não a recalcular nem inventar números.
    """
    linhas = []
    linhas.append(
        "Você é um especialista em FinOps. Interprete os dados de custo da AWS "
        "abaixo. NÃO invente valores: use somente os números fornecidos. "
        "Produza uma análise objetiva em português."
    )
    linhas.append("")
    linhas.append(f"Custo total do período: {analysis['total_cost']:.2f} USD")

    if analysis["has_positive_cost"]:
        linhas.append("Custo por serviço (valor e participação %):")
        for service, amount in sorted(
            analysis["positive_services"].items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            pct = analysis["percentages"].get(service, 0.0)
            linhas.append(f"- {service}: {amount:.2f} USD ({pct:.1f}%)")
        linhas.append(f"Serviço de maior custo: {analysis['largest_service']}")
    else:
        linhas.append("Não há serviços com custo positivo no período.")

    if comparison is not None:
        linhas.append("")
        linhas.append(
            f"Período anterior: {comparison['previous_total']:.2f} USD | "
            f"Período atual: {comparison['current_total']:.2f} USD"
        )
        if comparison["variation"] is not None:
            linhas.append(f"Variação: {comparison['variation']:.1f}%")
        else:
            linhas.append(
                "Variação percentual indisponível (período anterior com custo zero)."
            )

    linhas.append("")
    linhas.append(
        "Com base apenas nesses dados, aponte: os maiores custos, mudanças "
        "relevantes entre períodos, possíveis pontos de atenção e possíveis "
        "desperdícios. Seja direto."
    )
    return "\n".join(linhas)


def interpret(analysis, comparison):
    """Pede ao Llama uma interpretação dos dados de custo.

    Parâmetros
    ----------
    analysis : dict
        Saída de ``cost_analyzer.analyze_costs``.
    comparison : dict | None
        Saída de ``cost_analyzer.compare_periods``.

    Retorno
    -------
    str
        Texto de interpretação gerado pelo modelo.

    Levanta
    -------
    LlamaUnavailableError
        Quando o servidor Llama está indisponível ou retorna erro. O chamador
        decide como seguir (ex.: gerar o relatório sem a interpretação).
    """
    prompt = _build_prompt(analysis, comparison)
    url = f"{config.LLAMA_BASE_URL.rstrip('/')}/api/generate"

    try:
        response = requests.post(
            url,
            json={"model": config.LLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=config.LLAMA_TIMEOUT,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise LlamaUnavailableError(
            f"Não foi possível conectar ao Llama em {config.LLAMA_BASE_URL}. "
            "Verifique se o servidor (ex.: Ollama) está em execução."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise LlamaUnavailableError(
            f"O Llama não respondeu dentro de {config.LLAMA_TIMEOUT}s."
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise LlamaUnavailableError(
            f"Falha ao chamar o Llama: {exc}"
        ) from exc

    try:
        data = response.json()
    except (ValueError, json.JSONDecodeError) as exc:
        raise LlamaUnavailableError(
            "Resposta inesperada do Llama (não é um JSON válido)."
        ) from exc

    text = data.get("response")
    if not text:
        raise LlamaUnavailableError(
            "O Llama respondeu sem conteúdo de interpretação."
        )

    return text.strip()
