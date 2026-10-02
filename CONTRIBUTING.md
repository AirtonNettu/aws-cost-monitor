# Contribuindo — AWS Cost Monitor

Obrigado pelo interesse em contribuir. Este guia resume o fluxo de trabalho e os
padrões do projeto.

> English speakers: this project's primary language is Portuguese, but pull
> requests and issues in English are welcome.

## Princípio inegociável

**Python calcula. IA interpreta.** Qualquer valor financeiro deve ser produzido
por código Python determinístico (`src/analysis/`). A camada de IA
(`src/ai/`) apenas interpreta números já calculados — nunca os produz, estima
ou "arredonda". PRs que violem essa separação não serão aceitos.

## Pré-requisitos

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Python 3.14+

```bash
git clone https://github.com/AirtonNettu/aws-cost-monitor
cd aws-cost-monitor
uv sync --dev
```

## Fluxo de trabalho

1. Abra uma issue descrevendo o problema ou a proposta antes de um PR grande.
2. Crie um branch a partir de `main`: `git checkout -b feat/minha-mudanca`.
3. Faça a mudança, com testes cobrindo a lógica nova.
4. Rode a suíte: `uv run pytest -v`. Tudo precisa passar.
5. Abra o Pull Request descrevendo o quê, o porquê e como você testou.

## Padrões de código

- Siga o estilo existente (type hints, docstrings em português, funções que
  retornam dados estruturados).
- Toda nova lógica de cálculo precisa de testes determinísticos com mocks —
  nunca dependa da conta AWS real nem do Llama em CI.
- Trate erros de forma explícita; não mascare exceções.
- Mantenha a camada AWS isolada: apenas `src/aws/` importa `boto3`.
- Atualize o `README.md`, o `README.en.md` e os arquivos em `docs/` quando o
  comportamento mudar.

## Mensagens de commit

Prefira o formato [Conventional Commits](https://www.conventionalcommits.org/pt-br/):

```
feat: adiciona granularidade diária ao Cost Explorer
fix: corrige divisão por zero em compare_periods
docs: atualiza tabela de variáveis de ambiente
test: cobre resposta vazia do Llama
```

## Segurança

- **Nunca** faça commit de credenciais AWS, `.env`, relatórios ou dados reais.
- Reporte vulnerabilidades em uma issue privada ou por contato direto, não em um
  PR público.
