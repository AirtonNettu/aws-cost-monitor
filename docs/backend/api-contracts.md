# Contratos HTTP FastAPI — Especificação e Implementação (PR #7)

**Fonte do consumidor:** `frontend/src/api/contracts.ts` e `frontend/src/api/contracts.test.ts`.
**Status:** Implementado em `src/api/app.py` e 100% testado contra Pydantic v2 e Zod.

## Regras Globais
- Prefixo base `/api/v1`.
- JSON codificado em UTF-8.
- Datas ISO 8601 com timezone offset explícito em `collected_at` (UTC).
- Períodos `YYYY-MM-DD` com `start < end` estrito.
- Valores monetários finitos em USD (normalização de -0.0 para 0.0).
- `source`: `"aws"` ou `"mock"`.
- Identificador `id` tratado como string opaca nas rotas.
- Pydantic configurado com `extra="forbid"` para garantir consistência estrita com os esquemas Zod do frontend.
- Nenhum endpoint GET consulta o AWS Cost Explorer ou executa Ollama em tempo de requisição.

## Endpoints Implementados

| Método | Caminho | Resposta | Semântica |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | `{"status": "ok"}` | Verificação de disponibilidade da API. |
| GET | `/api/v1/snapshots/latest?days=7\|30\|90&tag=...` | `Snapshot` | Último snapshot **persistido** para o período e tag; 404 se não houver registro. |
| GET | `/api/v1/runs?limit=50&offset=0&days=...&tag=...` | `{"runs": [RunSummary]}` | Histórico ordenado com suporte a paginação e filtros. |
| GET | `/api/v1/runs/{id}` | `Snapshot` | Detalhes completos do snapshot imutável da execução. |
| GET | `/api/v1/runs/{id}/reports/{format}` | Arquivo (Download) | Exportação gerada em memória (`json`, `markdown`, `html`, `txt`). |

### Schema de Resposta: Snapshot
```json
{
  "id": "1",
  "source": "aws",
  "collected_at": "2026-10-29T22:30:00+00:00",
  "currency": "USD",
  "period": { "start": "2026-09-29", "end": "2026-10-29" },
  "estimated": false,
  "tag": null,
  "summary": {
    "total_cost": 1250.40,
    "largest_service": "Amazon EC2",
    "largest_service_percentage": 65.4,
    "alert_count": 2
  },
  "comparison": {
    "previous_total": 1000.00,
    "current_total": 1250.40,
    "variation": 25.04,
    "equivalent_periods": true,
    "previous_period": { "start": "2026-08-30", "end": "2026-09-29" }
  },
  "services": [
    { "name": "Amazon EC2", "amount": 817.76, "percentage": 65.4 }
  ],
  "timeline": [
    { "date": "2026-09-29", "amount": 42.10 }
  ],
  "alerts": [
    {
      "id": "1-1",
      "type": "growth",
      "severity": "warning",
      "message": "Custo total cresceu 25.0% em relação ao período anterior."
    }
  ],
  "ai": {
    "status": "ready",
    "text": "Resumo executivo gerado...",
    "model": "llama3",
    "observations": [],
    "recommendations": [],
    "potential_waste": [],
    "reason": null
  },
  "available_filters": {
    "days": [7, 30, 90],
    "tags": ["Environment: Production"]
  },
  "report_formats": ["json", "markdown", "html", "txt"]
}
```

### Schema de Resposta: HistoryResponse (`GET /runs`)
```json
{
  "runs": [
    {
      "id": "1",
      "collected_at": "2026-10-29T22:30:00+00:00",
      "period": { "start": "2026-09-29", "end": "2026-10-29" },
      "estimated": false,
      "total_cost": 1250.40,
      "largest_service": "Amazon EC2"
    }
  ]
}
```

## Códigos de Erro e Tratamento
- **404 Not Found:**
  - Snapshot não encontrado para o par `(days, tag)` informado.
  - Execução ID inexistente ou não-numérica.
  - Formato de exportação não suportado ou inexistente para o snapshot.
- **409 Conflict:**
  - Snapshot legado gravado com timestamp ingênuo sem informação de fuso horário UTC (`Snapshot legado sem fuso horario; migracao necessaria.`). Preserva a restrição de não fabricar dados ausentes.
- **422 Unprocessable Entity:**
  - Parâmetro `days` fora dos valores permitidos (7, 30, 90).
  - Parâmetro `limit` fora do intervalo `[1, 100]`.
- **CORS:**
  - Habilitado para origens autorizadas de frontend (`http://localhost:5173`, `http://127.0.0.1:5173`, etc.) restrito aos métodos `GET` e `OPTIONS`.
