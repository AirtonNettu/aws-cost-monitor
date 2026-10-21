# Plano de implementação e critérios de aceite

**Status:** planejamento técnico, **não autorização para codificar**. Nenhum código FastAPI/Ollama foi criado nesta entrega.

## Dependências e sequência técnica
| Ordem | Tarefa | Entregável e testes |
| --- | --- | --- |
| 1 | Revisão de contratos | Fechar OpenAPI/Pydantic com Zod; decidir auth, filtros, modelo de dados e endpoints IA. |
| 2 | Baseline Python | Rodar pytest/security audit, documentar falhas reais, garantir ambiente Python >=3.14 conforme pyproject. |
| 3 | Domínio e mappers | Mapear SQLite/FinOps para Snapshot; corrigir `untagged_resources` vs `untagged`; testar créditos, datas, equivalência. |
| 4 | Persistência | Migrações seguras para metadados, série temporal, IA; testes em SQLite temporário e rollback. |
| 5 | FastAPI leitura | `/snapshots/latest`, `/runs`, `/runs/{id}`; TestClient com mocks, sem AWS. |
| 6 | Segurança | Autenticação e autorização adequadas ao modo de publicação; CORS, erros, rate limits e logs. |
| 7 | Relatórios | Download autorizado com formatos realmente existentes, headers corretos e prevenção de path traversal. |
| 8 | Ollama provider | Interface de provider, configuração validada, timeouts, concorrência, JSON estruturado, fallback, cache e testes. |
| 9 | Orquestração IA | Jobs/estado, proveniência, persistência, API de solicitação/consulta; aprovação de extensão do contrato React. |
| 10 | Integração ponta a ponta | React em modo `api`, snapshots reais locais, estados de IA, testes de contrato e E2E. |
| 11 | Documentação de evidências | ADRs aprovadas, comandos, resultados medidos, screenshots e case de portfólio. |

## Contratos de aceite
- GET de UI não consulta Cost Explorer e não executa Ollama.
- Não há valores inventados, nem fallback silencioso de erro para mock.
- Snapshot mantém período de fim exclusivo, timezone, USD, créditos e estimated.
- API responde com o mesmo shape que `frontend/src/api/contracts.ts` valida.
- Erros HTTP têm códigos corretos, sem segredos nem stacktrace.
- Falha de IA não bloqueia FinOps.
- Nenhum teste automatizado depende de AWS/Ollama real.
- Casos negativos cobrem zero, créditos, dados ausentes, comparação não equivalente, timeout, JSON inválido, prompt injection e acesso não autorizado.
- Documentação distingue proposta, implementado e validado.
- Commits por tarefa, push em branch, revisão antes de merge; nenhum deploy sem autorização.

## Testes por camada
- **Domain:** pytest puro, determinismo, alertas, comparação, porcentagens.
- **Persistence:** SQLite temporário, migração, FK, transações, concorrência básica.
- **Application:** fake repository, fake provider IA, sem HTTP.
- **API:** TestClient, Pydantic, status codes, autorização, OpenAPI, downloads.
- **Contract:** fixtures Python serializadas e validadas por Zod no frontend.
- **Frontend:** Vitest e integração com servidor local, sem custos AWS.
- **IA:** dataset fixo, grounding, schemas, erros e latência simulada.
- **Manual:** Ollama instalado, modelo local e dados fictícios; documentar evidência.

## Checklist de decisões para sessão de implementação
- [ ] API somente local ou publicação web?
- [ ] Autenticação individual ou demonstração local isolada?
- [ ] Frequência máxima de coleta AWS e orçamento permitido?
- [ ] Modelo Ollama instalado e capacidade real do hardware?
- [ ] Inferência assíncrona por job ou síncrona?
- [ ] Retenção de snapshots e análises?
- [ ] Formatos de exportação que serão realmente suportados?
- [ ] Estratégia de migração e backup SQLite?

## Entrega no portfólio
**Problema:** custos AWS difíceis de acompanhar e interpretar.
**Solução:** dashboard React, dados determinísticos Python, API FastAPI e interpretação opcional Ollama.
**Evidências futuras:** PRs, testes, arquitetura, decisões, erros tratados, avaliação da IA, custo operacional e demonstração sem segredos. Não anunciar FastAPI ou IA robusta como concluídos antes da implementação e validação.
