# API v0.2 — contrato implementado

Factory: `uv run uvicorn src.api.app:create_app --factory --no-access-log --host 127.0.0.1 --port 8000`.
Variáveis privadas: `API_USERNAME` (default operator), `API_PASSWORD` obrigatória (16–256 caracteres ASCII), `DATABASE_PATH` (default data/costs.db). Não usar variáveis VITE para segredos.

Todas as rotas de dados exigem HTTP Basic do operador. `/health/live` é público e não consulta banco, AWS ou IA. `/health/ready` é autenticado e testa leitura da tabela de snapshots. Sem suporte multiusuário, coleta HTTP ou execução de prompts arbitrários.

| Método/rota | Resultado |
| --- | --- |
| GET /api/v1/snapshots/latest?days=7\|30\|90&tag=... | Snapshot salvo para janela e escopo exatos; 404 sem snapshot |
| GET /api/v1/runs?limit=1..50 | Histórico de snapshots completos, mais recentes primeiro |
| GET /api/v1/runs/{id} | Snapshot completo identificado por run numérico |
| GET /api/v1/runs/{id}/reports/json | Download do snapshot validado |
| GET /api/v1/runs/{id}/reports/csv | Download com neutralização de fórmulas em nomes |
| GET /api/v1/openapi.json | Contrato OpenAPI autenticado |

Os campos Snapshot/History seguem `frontend/src/api/contracts.ts` e os modelos em `src/application/snapshots.py`. Datas de período são YYYY-MM-DD, fim exclusivo; coleta tem timezone; números finitos USD, null não vira zero. `untagged_resources` é normalizado para `untagged`. `available_filters` anuncia somente janelas/tags persistidas. Tag é contexto de agrupamento, não filtro simultâneo SERVICE+TAG.

Formatos disponíveis na API: json e csv. Relatórios CLI txt/markdown/html continuam disponíveis localmente. A UI desabilita exportação de snapshots mock; downloads da API ainda podem ser verificados com cliente autenticado. source=mock é preservado no transporte HTTP real para demonstrações.

Erros: `{"error":{"code":"...","message":"...","request_id":"..."}}`.
401: autenticação; 404: snapshot ausente; 422: parâmetros/formato; 503: banco ou snapshot inválido; 500: falha interna segura. Não há papel parcialmente autorizado nesta versão: o único principal configurado pode ler o workspace inteiro; credenciais diferentes recebem 401. Não inventar respostas 403/429 como implementadas.

Toda resposta inclui X-Request-ID, Cache-Control:no-store e X-Content-Type-Options:nosniff. Correlation ID externo precisa ser UUID, senão um novo é gerado. Logs não registram Authorization, query string, corpo, conta ou custo. Timeout do cliente 15s; SQLite 5s; sem polling, retry HTTP ou coleta por GET.

Teste de interoperabilidade: `npm run test:contract` em frontend usa TestClient real, SQLite temporário, dados sintéticos e Zod. E2E de navegador valida separadamente o servidor Uvicorn com proxy Vite.

Estabilização PR #8: payload armazenado é validado como Snapshot antes de enriquecer filtros. JSON inválido, raiz não objeto e campos ausentes retornam503 INVALID_SNAPSHOT, sem conteúdo original em logs ou resposta. Autenticação e CORS não foram ampliados.
