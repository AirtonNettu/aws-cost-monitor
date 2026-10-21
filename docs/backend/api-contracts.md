# Contratos HTTP FastAPI — especificação proposta

**Fonte do consumidor:** `frontend/src/api/contracts.ts` e `docs/frontend/api-contract.md`. **Nenhum endpoint está implementado nesta etapa.** Contratos serão testados contra Zod antes de integração.

## O que é contrato de API?
É o acordo verificável entre quem fornece dados (FastAPI) e quem os consome (React): método, caminho, parâmetros, tipos, invariantes, resposta, erros, autorização e compatibilidade. FastAPI gera OpenAPI a partir dos modelos Pydantic; o frontend valida JSON com Zod. Os dois devem concordar.

## Regras globais
- Base `/api/v1`; JSON UTF-8; datas ISO 8601 com timezone em `collected_at`.
- Períodos `YYYY-MM-DD` com `start < end`; **end exclusivo**.
- Valores monetários em USD, números finitos; `null` não vira zero.
- `source`: `aws` ou `mock`; nunca misturar silenciosamente.
- Identificador `id` opaco, não inferir sequencialidade nem expor IDs de terceiros.
- Campos desconhecidos e valores incompatíveis: corrigir contrato, não falsificar.
- Segurança: 401 sem autenticação, 403 sem autorização, 404 recurso inexistente, 422 filtros inválidos, 429 limite, 5xx erro seguro; 503 para dependência crítica indisponível quando aplicável.
- Não incluir traceback, caminho de arquivo local ou dados sensíveis em erros.

## Endpoints de leitura já acordados com o frontend
| Método | Caminho | Semântica |
| --- | --- | --- |
| GET | `/snapshots/latest?days=7|30|90&tag=...` | Último snapshot **persistido** para período/tag; nunca coleta AWS. |
| GET | `/runs?limit=50` | Lista de execuções recentes; resposta `{"runs":[...]}`. |
| GET | `/runs/{id}` | Snapshot imutável da execução. |
| GET | `/runs/{id}/reports/{format}` | Download somente quando `format` está em `report_formats`. |

### Snapshot obrigatório (resumo fiel do Zod)
```json
{
  "id": "run-42",
  "source": "aws",
  "collected_at": "2026-10-21T12:00:00-03:00",
  "currency": "USD",
  "period": {"start": "2026-09-21", "end": "2026-10-21"},
  "estimated": true,
  "tag": null,
  "summary": {
    "total_cost": 12.5,
    "largest_service": "Amazon EC2",
    "largest_service_percentage": 80.0,
    "alert_count": 1
  },
  "comparison": null,
  "services": [{"name": "Amazon EC2", "amount": 10.0, "percentage": 80.0}],
  "timeline": [],
  "alerts": [{"id": "alert-1", "type": "concentration", "severity": "warning", "message": "Concentracao acima do limite configurado."}],
  "ai": {"status": "unavailable", "text": null, "model": null, "observations": [], "recommendations": [], "potential_waste": [], "reason": "Analise ainda nao executada."},
  "available_filters": {"days": [7, 30, 90], "tags": []},
  "report_formats": []
}
```
Exemplo **ilustrativo**, não extraído de conta AWS real.

### RunSummary
`id`, `collected_at`, `period`, `estimated`, `total_cost`, `largest_service`. `GET /runs` retorna `{"runs": [RunSummary, ...]}`.

### Regras financeiras de contrato
- `summary.total_cost` inclui créditos/ajustes; não recomputar no navegador.
- `services` e percentuais vêm prontos do Python. Percentuais podem ter particularidades quando créditos reduzem o total.
- `comparison.variation` é `null` se base zero ou comparação não disponível; `equivalent_periods` deve ser comprovado por duração e escopo iguais.
- `timeline: []` se o banco ainda não contém dados diários; não fabricar.
- `available_filters.tags` exige descoberta/cache/autorização real; não inferir de strings.
- `ai` deve existir, mesmo indisponível, com arrays vazios quando apropriado.
- Exportação só deve anunciar formatos realmente disponíveis e autorizados.

## Endpoint de IA: proposta adicional, NÃO suportada ainda pelo frontend
`POST /api/v1/runs/{id}/ai-analyses` — solicitar interpretação de snapshot persistido, autenticada, limitada por usuário, sem coleta AWS. A forma de processamento será definida: síncrona com timeout limitado **ou**, preferencialmente para CPU local, assíncrona com job id e `GET /api/v1/ai-analyses/{job_id}`. Antes de implementar, aprovar a extensão dos schemas frontend; o contrato atual só apresenta status dentro de Snapshot.

Exemplo conceitual de resposta de job:
```json
{"id":"ai-job-42","run_id":"run-42","status":"queued"}
```
Não implementar POST genérico que aceite URL arbitrária do Ollama ou prompt sem controle.

## Erros
Formato recomendado (a definir em ADR): `{"error":{"code":"SNAPSHOT_NOT_FOUND","message":"Snapshot nao encontrado.","request_id":"..."}}`. Testes devem cobrir 401/403/404/422/429/500/503, timeout, body inválido, cancelamento e dados não finitos.

## Como construir e manter o contrato
1. Escrever cenário e invariantes.
2. Definir `BaseModel` Pydantic com `Field`, enums, validators e `response_model`.
3. Criar caso de uso independente do FastAPI.
4. Criar endpoint com DI e mapeamento de erros.
5. Gerar e revisar `/openapi.json`.
6. Rodar testes FastAPI/TestClient e contrato com fixtures compartilhadas.
7. Validar o JSON real com o schema Zod já existente.
8. Versionar mudança incompatível; atualizar docs, frontend e testes no mesmo ciclo.
