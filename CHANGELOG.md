# Changelog

Todas as mudanças relevantes deste projeto são documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e o projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Planejado
- Sistema de alertas push (notificações SNS / Slack a partir das regras de FinOps).
- Suporte a outros provedores de IA (OpenAI, Claude, Gemini, Bedrock).
- Evolução para arquitetura serverless (Lambda, EventBridge, SNS, CloudWatch).

## [0.2.0] — 2026-10-13

### Adicionado
- Dashboard interativo moderno com Streamlit (`dashboard.py` / `src/dashboard/app.py`), exibindo KPIs executivos, gráfico temporal, distribuição por serviço, ranking e central de alertas FinOps.
- Novo formato de relatório HTML standalone (`build_report_html` / `--format html`) com Tailwind styling e gráfico interativo via Chart.js.
- Persistência local em SQLite (`src/database/repository.py` / `data/costs.db`) para histórico de execuções e análise de tendências de longo prazo.
- Interface de linha de comando com argumentos (`argparse`), com flags `--days`, `--granularity`, `--format`, `--no-ai`, `--dashboard` e `--no-db`.
- Suporte a granularidade `DAILY` e tratamento de paginação automática (`NextPageToken`) em `src/aws/cost_explorer.py`.
- Suíte de testes expandida para 51 testes unitários com mocks cobrindo todas as novas funcionalidades.

## [0.1.0] — 2026-10-01

### Adicionado
- Ambiente Python gerenciado com `uv`.
- Verificação de conexão com a AWS via STS `get_caller_identity` (`src/test_aws.py`).
- Coleta de custos no AWS Cost Explorer com parâmetros configuráveis
  (região, janela de dias, granularidade, métrica), em `src/aws/cost_explorer.py`.
- Análise determinística retornando dados estruturados — total, serviços positivos,
  percentuais e maior serviço — em `src/analysis/cost_analyzer.py`.
- Comparação entre períodos com tratamento seguro de divisão por zero.
- Regras determinísticas de FinOps (crescimento, concentração e top N) com limiares
  configuráveis, em `src/analysis/finops_rules.py`.
- Camada de IA (Llama local) desacoplada e não-bloqueante, com tratamento de
  indisponibilidade via `LlamaUnavailableError`, em `src/ai/llama_client.py`.
- Geração e gravação de relatório em três formatos (texto, JSON e Markdown),
  em `src/reports/report_generator.py`.
- Orquestração do fluxo completo em `src/main.py` com tratamento de erro por etapa.
- Configuração centralizada em `src/config.py` (via `.env` / variáveis de ambiente).
- Suíte de testes com `pytest` e mocks, sem dependência da conta AWS real.
- Documentação técnica em `docs/`.
- Licença MIT.

[Não lançado]: https://github.com/AirtonNettu/aws-cost-monitor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/AirtonNettu/aws-cost-monitor/releases/tag/v0.1.0
