# Documentação técnica — AWS Cost Monitor V1

Documentação derivada do código real do repositório. Descreve como o sistema funciona hoje, sem funcionalidades planejadas.

## Índice

- [architecture.md](architecture.md) — objetivo, componentes, fluxo, decisões arquiteturais.
- [code-structure.md](code-structure.md) — estrutura de diretórios e detalhe por arquivo (inclui `finops_rules.py`).
- [data-flow.md](data-flow.md) — fluxo de dados da AWS ao relatório (com diagramas).
- [configuration.md](configuration.md) — variáveis de ambiente e defaults (inclui limiares de FinOps e `REPORT_FORMAT`).
- [aws-permissions.md](aws-permissions.md) — serviços, APIs e permissões IAM.
- [ai-integration.md](ai-integration.md) — camada Llama e tratamento de indisponibilidade.
- [reports.md](reports.md) — formatos (txt/json/markdown), alertas de FinOps e tratamento de valores.
- [error-handling.md](error-handling.md) — todos os caminhos de erro.
- [testing.md](testing.md) — testes, mocks e cobertura real.
- [setup.md](setup.md) — requisitos e instalação.
- [development.md](development.md) — comandos de execução e sequência principal.
- [troubleshooting.md](troubleshooting.md) — problemas reais e soluções.

## Regra arquitetural

**Python calcula. IA interpreta.** Os valores financeiros são produzidos exclusivamente por `src/analysis/cost_analyzer.py`. A camada de IA (`src/ai/llama_client.py`) apenas interpreta os números já calculados.
