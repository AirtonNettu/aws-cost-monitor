"""Testes do cliente de IA, mockando a camada HTTP (requests)."""

import pytest
import requests

from src.ai import llama_client
from src.ai.llama_client import LlamaUnavailableError, interpret
from src.analysis.cost_analyzer import analyze_costs


class _FakeResponse:
    def __init__(self, json_data, raise_exc=None):
        self._json = json_data
        self._raise = raise_exc

    def raise_for_status(self):
        if self._raise:
            raise self._raise

    def json(self):
        return self._json


def test_interpret_retorna_texto(monkeypatch, costs_single_period):
    analysis = analyze_costs(costs_single_period)

    def fake_post(url, json, timeout):
        return _FakeResponse({"response": "Interpretação gerada."})

    monkeypatch.setattr(llama_client.requests, "post", fake_post)
    result = interpret(analysis, None)
    assert result == "Interpretação gerada."


def test_interpret_erro_de_conexao(monkeypatch, costs_single_period):
    analysis = analyze_costs(costs_single_period)

    def fake_post(url, json, timeout):
        raise requests.exceptions.ConnectionError()

    monkeypatch.setattr(llama_client.requests, "post", fake_post)
    with pytest.raises(LlamaUnavailableError):
        interpret(analysis, None)


def test_interpret_timeout(monkeypatch, costs_single_period):
    analysis = analyze_costs(costs_single_period)

    def fake_post(url, json, timeout):
        raise requests.exceptions.Timeout()

    monkeypatch.setattr(llama_client.requests, "post", fake_post)
    with pytest.raises(LlamaUnavailableError):
        interpret(analysis, None)


def test_interpret_resposta_sem_conteudo(monkeypatch, costs_single_period):
    analysis = analyze_costs(costs_single_period)

    def fake_post(url, json, timeout):
        return _FakeResponse({"response": ""})

    monkeypatch.setattr(llama_client.requests, "post", fake_post)
    with pytest.raises(LlamaUnavailableError):
        interpret(analysis, None)


def test_prompt_nao_recalcula_usa_valores_fornecidos(costs_single_period):
    # O prompt deve conter os valores já calculados pelo Python.
    analysis = analyze_costs(costs_single_period)
    prompt = llama_client._build_prompt(analysis, None)
    assert "50.00 USD" in prompt
    assert "Amazon EC2" in prompt
    assert "NÃO invente valores" in prompt
