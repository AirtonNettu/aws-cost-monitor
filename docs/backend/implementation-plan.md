# Plano de Implementação e Critérios de Aceite — PR #7

**Status:** Concluído na branch `feat/fastapi-snapshot-api`. Pronto para revisão humana (Ponto de parada: sem merge).

## Sequência Técnica Executada
| Ordem | Tarefa | Status | Entregável e Testes |
| --- | --- | --- | --- |
| 1 | Revisão de Contratos | ✅ Concluído | Alinhamento Pydantic v2 com Zod (`contracts.ts` e `contracts.test.ts`). |
| 2 | Baseline Python & QA | ✅ Concluído | Pytest com 72 testes aprovados; Vitest com 43 testes aprovados. |
| 3 | Mapeamento e Regras FinOps | ✅ Concluído | Mapeamento `untagged_resources` -> `untagged`, cálculo de equivalência de períodos e percentuais. |
| 4 | Persistência & Migração SQLite | ✅ Concluído | Migração incremental idempotente em `src/database/repository.py` com índices de busca. |
| 5 | FastAPI Endpoints de Leitura | ✅ Concluído | `/health`, `/snapshots/latest`, `/runs`, `/runs/{id}`, `/runs/{id}/reports/{format}`. |
| 6 | Segurança & Auditoria | ✅ Concluído | Execução de `scripts/security_audit.py` com 0 alertas e 0 achados. |
| 7 | Download Seguro de Relatórios | ✅ Concluído | Geração in-memory de relatórios nos formatos `json`, `markdown`, `html`, `txt` sem path traversal. |
| 8 | Semeadura Sintética | ✅ Concluído | `src/database/seeds.py` e `scripts/seed_snapshots.py` carregando fixtures para frontend. |
| 9 | Integração React Vite Proxy | ✅ Concluído | `frontend/vite.config.ts` com proxy reverso `/api` apontando para o backend FastAPI local. |
| 10 | Documentação & ADRs | ✅ Concluído | ADR-007, ADR-008 e ADR-009 documentadas em `docs/backend/architecture.md`. |
| 11 | Revisão Corretiva da PR #7 | ✅ Concluído | Equivalência estrita de períodos, paginação consistente em `/runs` e validação de números finitos. |

## Critérios de Aceite Atendidos
- [x] GET de UI não consulta Cost Explorer e não executa Ollama.
- [x] Não há valores inventados no banco legado; snapshots sem timezone retornam 409 em vez de inventar UTC.
- [x] Snapshot mantém período com fim exclusivo (`start < end`), timezone UTC, USD, créditos e estimated.
- [x] API responde com o mesmo formato estrito que `frontend/src/api/contracts.ts` valida via Zod.
- [x] Erros HTTP têm códigos semânticos e seguros (404, 409, 422, 500), sem segredos nem stack traces.
- [x] Falha ou ausência de IA não bloqueia dados FinOps (status `unavailable`).
- [x] Nenhum teste automatizado depende de AWS ou Ollama real.
- [x] Preservado o funcionamento do Streamlit (`src/dashboard/app.py`) e da CLI (`src/main.py`).
- [x] Build de produção do frontend (`tsc -b && vite build`) concluído com sucesso.
- [x] `equivalent_periods` valida metadados, mesma duração, sem sobreposição e escopos idênticos.
- [x] `/api/v1/runs` utiliza `only_compatible=True` no SQL, garantindo paginação consistente e eliminando descarte silencioso.
- [x] Proibição rigorosa de `NaN`, `Infinity` e `-Infinity` em Pydantic e SQLite, com preservação de créditos negativos.
- [x] Workflow GitHub Actions configurado com permissões mínimas (`contents: read`) e sem chamadas externas.
