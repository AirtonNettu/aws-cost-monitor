import { snapshotSchema, historySchema, type DataClient, type Snapshot } from '../api/contracts'
import fixtures from './fixtures.json'

const scenarios = ['success', 'empty', 'error', 'loading', 'ai-unavailable', 'ai-processing']

export function createMockClient(scenario = 'success', delay = 300): DataClient {
  if (!scenarios.includes(scenario)) throw new Error('Cenário mock desconhecido.')
  const wait = (signal?: AbortSignal) => new Promise<void>((resolve, reject) => {
    if (signal?.aborted) { reject(new DOMException('Cancelado', 'AbortError')); return }
    const abort = () => { clearTimeout(timer); reject(new DOMException('Cancelado', 'AbortError')) }
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', abort)
      if (scenario === 'error') reject(new Error('Falha simulada. Tente novamente ou altere o cenário de demonstração.'))
      else resolve()
    }, scenario === 'loading' ? 8000 : delay)
    signal?.addEventListener('abort', abort, { once: true })
  })
  function transform(input: unknown): Snapshot {
    const data = snapshotSchema.parse(structuredClone(input))
    if (scenario === 'empty') {
      data.summary = { total_cost: 0, largest_service: null, largest_service_percentage: null, alert_count: 0 }
      data.services = []; data.timeline = []; data.alerts = []; data.comparison = null
      data.ai = { status: 'unavailable', text: null, model: null, observations: [], recommendations: [], potential_waste: [], reason: 'Sem dados para interpretar.' }
    } else if (scenario === 'ai-unavailable' || scenario === 'ai-processing') {
      data.ai = { status: scenario === 'ai-processing' ? 'processing' : 'unavailable', text: null, model: null, observations: [], recommendations: [], potential_waste: [], reason: 'A integração com o modelo está indisponível neste cenário simulado.' }
    }
    return data
  }
  return {
    mode: 'mock',
    async getSnapshot(filters, signal) {
      await wait(signal)
      const snapshots: Record<string, unknown> = fixtures.snapshots
      const data = snapshots[`${filters.days}:${filters.tag}`]
      if (!data) throw new Error('Filtro não disponível neste cenário.')
      return transform(data)
    },
    async getHistory(signal) {
      await wait(signal)
      return historySchema.parse({ runs: scenario === 'empty' ? [] : fixtures.runs.map(run => ({
        id: run.id, collected_at: run.collected_at, period: run.period, estimated: run.estimated,
        total_cost: run.summary.total_cost, largest_service: run.summary.largest_service,
      })) })
    },
    async getRun(id, signal) {
      await wait(signal)
      const run = fixtures.runs.find(run => run.id === id)
      if (!run) throw new Error('Execução não encontrada.')
      return transform(run)
    },
    async exportReport() { throw new Error('Exportação depende do futuro backend.') },
  }
}
