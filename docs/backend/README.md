# Backend Python + FastAPI + Ollama — pacote de especificação

**Estado:** proposta técnica documentada; **não implementada**. Branch: `docs/fastapi-ollama-architecture`. Frontend React integrado à `main` pelo PR #5. Não confundir contrato proposto com endpoint ativo.

## Índice de leitura
1. [Arquitetura](architecture.md) — componentes, fluxos, limites e ADRs.
2. [Contratos HTTP](api-contracts.md) — rotas, schemas, erros e exemplos.
3. [Engenharia de IA](ai-integration.md) — Ollama, segurança, saídas e avaliação.
4. [Dados, segurança e FinOps](data-security.md) — SQLite, AWS, autorização e custos.
5. [Plano de implementação e testes](implementation-plan.md) — ordem técnica, aceites e riscos.
6. [Contrato existente do frontend](../frontend/api-contract.md) — fonte inicial das tipagens Zod.

## Escopo
Conectar a SPA React ao backend Python sem duplicar cálculos. Servir snapshots persistidos, histórico e relatórios com autorização. Evoluir a integração local Ollama existente com estruturação, observabilidade e avaliação. O backend continuará em Python; Node é apenas ferramenta do frontend.

## Situação verificada no código
- `src/aws/cost_explorer.py`: boto3 Cost Explorer com períodos, paginação e agrupamento SERVICE **ou** TAG.
- `src/analysis/cost_analyzer.py`: total, ranking, percentuais, comparação determinística.
- `src/analysis/finops_rules.py`: regras growth, concentration, top_services e untagged_resources.
- `src/database/repository.py`: SQLite com tabelas runs e service_costs; histórico sem série diária completa.
- `src/ai/llama_client.py`: POST /api/generate, texto livre, timeout e erros explícitos.
- `src/main.py`: CLI/orquestrador; Streamlit preservado.
- `frontend/src/api/contracts.ts`: schema de snapshot esperado pelo React.
- **FastAPI não consta como implementado**; nenhuma API real foi testada neste pacote.

## Princípios
**React apresenta. FastAPI orquestra. Python calcula. Ollama interpreta.**
Dados financeiros são produzidos e validados em Python. LLM não autoriza ações nem altera custos. A indisponibilidade de IA não bloqueia a visualização FinOps. Custo zero é objetivo sujeito à verificação de preços e limites AWS, não garantia.

## Processo de aprovação
Documentação pode ser revisada e ajustada antes de implementação. Cada etapa de código exige testes, commit por tarefa e branch de trabalho; sem merge, deploy ou alteração de `main` sem aprovação.
