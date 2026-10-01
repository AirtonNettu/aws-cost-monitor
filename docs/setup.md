# Setup — AWS Cost Monitor V1

> Comandos e requisitos derivados de `pyproject.toml`, `.python-version` e do README.

## Requisitos

- **Python** `>= 3.14` (declarado em `pyproject.toml`; `.python-version` fixa `3.14`).
- **uv** (gerenciador de ambiente/dependências).
- **AWS CLI** configurado com credenciais (para o fluxo real; ver [aws-permissions.md](aws-permissions.md)).
- **Servidor Llama** local opcional (ex.: Ollama) para a interpretação por IA; ver [ai-integration.md](ai-integration.md).

## Dependências (de `pyproject.toml`)

Runtime:
- `boto3>=1.43.104`
- `python-dotenv>=1.2.3`
- `requests>=2.32.0`

Desenvolvimento (grupo `dev`):
- `pytest>=8.0.0`

## Instalação

```bash
git clone <url-do-repositorio>
cd aws-cost-monitor
uv sync --dev
```

`uv sync --dev` cria o ambiente virtual (`.venv/`) e instala runtime + grupo dev conforme travado em `uv.lock`.

## Configurar a AWS

```bash
aws configure
```

O boto3 usa automaticamente essas credenciais. Nenhuma credencial é colocada no projeto.

## (Opcional) Configurar `.env`

A aplicação roda sem `.env` (há defaults). Para personalizar, crie um `.env` na raiz com as variáveis descritas em [configuration.md](configuration.md). O `.env` é ignorado pelo Git.

## Verificar a instalação

```bash
# Testes (não exigem AWS nem Llama)
uv run pytest -v

# Verificação de credenciais AWS (exige AWS configurada)
uv run python src/test_aws.py
```

## Executar

Ver [development.md](development.md) para todos os comandos de execução.
