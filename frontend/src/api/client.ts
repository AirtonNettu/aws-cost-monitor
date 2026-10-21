import { historySchema, snapshotSchema, type DataClient } from './contracts'
import { fetchResponse, request } from './http'

export function createApiClient(base: string): DataClient {
  return {
    mode: 'api',
    getSnapshot: (filters, signal) => {
      const query = new URLSearchParams({ days: String(filters.days) })
      if (filters.tag) query.set('tag', filters.tag)
      return request(base, `snapshots/latest?${query}`, snapshotSchema, { signal })
    },
    getHistory: signal => request(base, 'runs?limit=50', historySchema, { signal }),
    getRun: (id, signal) => request(base, `runs/${encodeURIComponent(id)}`, snapshotSchema, { signal }),
    exportReport: async (id, format, signal) => {
      const response = await fetchResponse(base, `runs/${encodeURIComponent(id)}/reports/${format}`, { signal })
      return response.blob()
    },
  }
}

export async function createDataClient(): Promise<DataClient> {
  const mode = import.meta.env.VITE_DATA_MODE ?? 'mock'
  if (mode === 'mock') {
    const { createMockClient } = await import('../mocks/adapter')
    return createMockClient(import.meta.env.VITE_MOCK_SCENARIO ?? 'success')
  }
  if (mode !== 'api') throw new Error('VITE_DATA_MODE deve ser mock ou api.')
  return createApiClient(import.meta.env.VITE_API_BASE_URL ?? '/api/v1')
}
