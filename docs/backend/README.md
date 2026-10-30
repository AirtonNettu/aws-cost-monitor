# Backend Python + FastAPI — Implementação de Leitura e Contratos (PR #7)

**Estado:** Implementado e validado na branch `feat/fastapi-snapshot-api`. Endpoints de leitura da API FastAPI ativos, compatíveis com os contratos Zod do frontend React, apoiados por migração incremental do SQLite e suíte completa de testes.

## Índice de leitura
1. [Arquitetura](architecture.md) — componentes, fluxos, limites, ADRs e decisões da PR #7.
2. [Contratos HTTP](api-contracts.md) — rotas implementadas, schemas Pydantic, respostas, erros e mapeamento Zod.
3. [Engenharia de IA](ai-integration.md) — Ollama, desacoplamento, estados no Snapshot (`ai`) e evolução futura.
4. [Dados, segurança e FinOps](data-security.md) — SQLite, migração incremental, proteção contra vazamento e limites de custo.
5. [Plano de implementação e testes](implementation-plan.md) — checklist de tarefas, critérios de aceite atendidos e evidências.
6. [Contrato existente do frontend](../frontend/api-contract.md) — especificação TypeScript/Zod consumida pelo React.

## Escopo Realizado na PR #7
Conectar a SPA React ao backend Python FastAPI sem duplicar cálculos FinOps nem invocar chamadas com custo à AWS em requisições HTTP:
- **API FastAPI (`src/api/app.py`):** endpoints `/api/v1/health`, `/api/v1/snapshots/latest`, `/api/v1/runs`, `/api/v1/runs/{id}` e `/api/v1/runs/{id}/reports/{format}`.
- **Modelos Pydantic v2:** alinhamento estrito (`extra="forbid"`) com schemas Zod (`snapshotSchema`, `historySchema`).
- **Migração Incremental do SQLite (`src/database/repository.py`):** adição segura de colunas de metadados (`source`, `tag`, `days`, `estimated`, `timeline_json`, `comparison_json`, `ai_json`, `available_filters_json`, `report_formats_json`) sem perda de dados legados e criação de índices otimizados.
- **Semeadura Sintética (`src/database/seeds.py` e `scripts/seed_snapshots.py`):** carga de dados sintéticos fiéis às fixtures para desenvolvimento e testes ponta a ponta sem dependência de credenciais ou rede AWS.
- **Segurança e Isolamento:** relatórios gerados em memória prevenindo path traversal; CORS restrito; nenhum segredo ou dado sensível exposto em erros.

## Princípios Inegociáveis
**React apresenta. FastAPI orquestra. Python calcula. Ollama interpreta.**
- Todas as rotas de leitura servem snapshots locais persistidos.
- Nenhuma rota HTTP GET realiza requisição à AWS ou aciona inferência de IA.
- Valores ausentes no banco legado não são fabricados: snapshots legados sem timezone UTC retornam HTTP 409 em vez de falsificar fuso horário.
