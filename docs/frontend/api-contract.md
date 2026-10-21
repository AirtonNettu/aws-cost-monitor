# Contrato HTTP proposto — v1

**Proposta para aprovação posterior. Nenhum endpoint FastAPI existe nesta entrega.**
Os tipos e validações executáveis estão em `frontend/src/api/contracts.ts` (Zod + TypeScript).

## Rotas de leitura propostas

Base: `VITE_API_BASE_URL` (default `/api/v1`).

| Método/rota | Resposta | Semântica |
| --- | --- | --- |
| GET `/snapshots/latest?days=7\|30\|90&tag=…` | Snapshot | Último snapshot salvo para o período/tag, sem coletar AWS. Tag omitida significa todos. |
| GET `/runs?limit=50` | `{runs: RunSummary[]}` | Execuções recentes. Ordem preferida mais recente primeiro; cliente não depende dela. |
| GET `/runs/{id}` | Snapshot | Snapshot imutável. Identificador escapado como segmento de URL. |
| GET `/runs/{id}/reports/{format}` | arquivo binário | Apenas formatos anunciados em report_formats; respeitar mesmo controle de acesso do snapshot. |

Filtros não suportados: 422. Snapshot/run inexistente: 404. Falha: 5xx. Cliente exibe mensagem segura por código, sem corpo/traceback. 200 com payload inválido é erro de contrato, sem conversão automática para zero ou mocks.

## Snapshot

Campos obrigatórios (arrays podem estar vazios, null é explícito):

```typescript
interface Snapshot {
  id: string;
  source: 'mock' | 'aws';
  collected_at: string; // ISO 8601 com timezone
  currency: 'USD';
  period: {start: string; end: string}; // YYYY-MM-DD, start < end, fim EXCLUSIVO
  estimated: boolean;
  tag: string | null; // agrupamento/escopo aplicado no servidor
  summary: {
    total_cost: number; // finito, inclui créditos
    largest_service: string | null;
    largest_service_percentage: number | null;
    alert_count: number; // inteiro >= 0, todos os alertas incluindo informativos
  };
  comparison: null | {
    previous_total: number; current_total: number;
    variation: number | null; // percentual PRONTO, null para base zero/indisponível
    equivalent_periods: boolean;
    previous_period: {start: string; end: string};
  };
  services: {name: string; amount: number; percentage: number}[];
  timeline: {date: string; amount: number}[];
  alerts: {
    id: string; type: 'growth' | 'concentration' | 'top_services' | 'untagged';
    severity: 'info' | 'warning' | 'critical'; message: string;
  }[];
  ai: {
    status: 'ready' | 'processing' | 'unavailable';
    text: string | null; model: string | null;
    observations: string[]; recommendations: string[]; potential_waste: string[];
    reason: string | null;
  };
  available_filters: {days: (7 | 30 | 90)[]; tags: string[]};
  report_formats: ('json' | 'csv' | 'html' | 'markdown' | 'txt')[];
}
```

`RunSummary`: id, collected_at, period, estimated, total_cost, largest_service. Histórico permite comparar duas execuções lado a lado, sem inferir equivalência nem calcular delta.

## Adaptação necessária no futuro Python/FastAPI

- Reutilizar analyze_costs, generate_alerts e dados SQLite; preservar ajuste/crédito no total. Serviço e percentual vêm prontos. Não somar períodos no navegador.
- Determinar equivalent_periods comparando intervalos completos de mesma duração/escopo. O compare_periods atual, sozinho, não garante isso. UI oculta variação em períodos não equivalentes.
- Não gerar timeline histórica artificial: SQLite hoje só guarda agregados; retornar [] quando indisponível. Para série temporal diária, persistir os dados no backend em trabalho separado.
- Lista de tags disponíveis exige descoberta/autorização/cache no backend. get_costs(tag_key=...) hoje troca agrupamento de serviço por tag; não alegar cruzamento tag/serviço já implementado. Frontend apresenta nomes recebidos sem inferência.
- Alertas atuais são de limiar, concentração, ranking e untagged. Detecção estatística de anomalias é roadmap.
- Ollama atual retorna texto livre. Preservar text; arrays estruturados vazios e model=null quando não forem fornecidos. Criar estruturação e processamento assíncrono apenas em tarefa futura.
- Expor downloads gerados pelo Python só quando implementados; mocks anunciam report_formats=[]. Não há download falso.
- API deve servir snapshots cacheados; atualizar a tela não deve executar Cost Explorer. Respeitar limite de coleta e permissões do AGENTS.md.
- Autenticação, autorização por snapshot, CORS restrito, política de cache e segurança de downloads são trabalhos do backend antes de uso real. Frontend não recebe chaves AWS ou credenciais Ollama.

## Cliente

Timeout padrão de 15 segundos, cancelamento via AbortSignal, sem retries automáticos nem polling/foco. Erros podem ser repetidos manualmente. Nenhuma falha HTTP cai silenciosamente em mock. Toda variável VITE_* é pública e incorporada no build. As fixtures são sintéticas, estáticas e calculadas anteriormente com os módulos Python; não consultam serviços.
