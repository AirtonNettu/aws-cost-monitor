"""Configuração centralizada da aplicação.

Lê variáveis de ambiente (opcionalmente de um arquivo .env via python-dotenv)
e expõe os parâmetros usados pelos demais módulos. Mantém defaults seguros
para que a aplicação funcione sem configuração extra.

Nenhuma credencial AWS é lida ou armazenada aqui: o boto3 usa as credenciais
configuradas localmente (AWS CLI / variáveis de ambiente padrão da AWS).
"""

import os

from dotenv import load_dotenv

# Carrega variáveis de um arquivo .env na raiz do projeto, se existir.
load_dotenv()


def _get_int(name, default):
    """Lê uma variável de ambiente como inteiro, com fallback para o default."""
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError(
            f"A variável de ambiente {name}='{value}' não é um inteiro válido."
        )


# --- AWS / Cost Explorer -------------------------------------------------
# O Cost Explorer é um serviço global, mas o endpoint boto3 usa us-east-1.
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Janela de análise, em dias, a partir da data atual.
COST_PERIOD_DAYS = _get_int("COST_PERIOD_DAYS", 30)

# Granularidade e métrica usadas na consulta ao Cost Explorer.
COST_GRANULARITY = os.getenv("COST_GRANULARITY", "MONTHLY")
COST_METRIC = os.getenv("COST_METRIC", "UnblendedCost")


# --- IA / Llama ----------------------------------------------------------
# Endpoint de um servidor Llama local compatível com a API /api/generate do
# Ollama. Mantido desacoplado: trocar o provedor significa trocar este cliente.
LLAMA_BASE_URL = os.getenv("LLAMA_BASE_URL", "http://localhost:11434")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "llama3")
LLAMA_TIMEOUT = _get_int("LLAMA_TIMEOUT", 60)

# Permite desligar a camada de IA explicitamente (relatório sai sem interpretação).
AI_ENABLED = os.getenv("AI_ENABLED", "true").strip().lower() in {"1", "true", "yes"}


# --- Relatórios ----------------------------------------------------------
REPORTS_DIR = os.getenv("REPORTS_DIR", "reports")
