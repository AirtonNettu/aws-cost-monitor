import { afterEach, expect, it, vi } from 'vitest'
import { createApiClient, createDataClient } from './client'
import fixtures from '../mocks/fixtures.json'

afterEach(() => vi.unstubAllEnvs())
it('uses encoded filters, identifiers, and documented read routes', async () => {
  const fetcher = vi
    .spyOn(globalThis, 'fetch')
    .mockImplementation(async (url) => {
      return new Response(
        JSON.stringify(
          String(url).includes('runs?') ? { runs: [] } : fixtures.runs[0],
        ),
      )
    })
  const client = createApiClient('https://api.example.test/api/v1/')
  await client.getSnapshot({ days: 7, tag: 'R&D: Produção' })
  expect(fetcher.mock.calls[0]?.[0]).toBe(
    'https://api.example.test/api/v1/snapshots/latest?days=7&tag=R%26D%3A+Produ%C3%A7%C3%A3o',
  )
  expect(await client.getHistory()).toEqual({ runs: [] })
  await client.getRun('a/b')
  expect(fetcher.mock.calls[2]?.[0]).toBe(
    'https://api.example.test/api/v1/runs/a%2Fb',
  )
  const report = await client.exportReport('a/b', 'json')
  expect(report.size).toBeGreaterThan(0)
  expect(fetcher.mock.calls[3]?.[0]).toBe(
    'https://api.example.test/api/v1/runs/a%2Fb/reports/json',
  )
})
it('does not add an empty tag and rejects invalid API data', async () => {
  const fetcher = vi
    .spyOn(globalThis, 'fetch')
    .mockResolvedValue(new Response('{}'))
  await expect(
    createApiClient('/api/v1').getSnapshot({ days: 30, tag: '' }),
  ).rejects.toThrow('Resposta inválida')
  expect(fetcher.mock.calls[0]?.[0]).toBe('/api/v1/snapshots/latest?days=30')
})
it('selects the requested transport and rejects configuration typos', async () => {
  vi.stubEnv('VITE_DATA_MODE', 'mock')
  vi.stubEnv('VITE_MOCK_SCENARIO', 'success')
  expect((await createDataClient()).mode).toBe('mock')
  vi.stubEnv('VITE_DATA_MODE', 'api')
  expect((await createDataClient()).mode).toBe('api')
  vi.stubEnv('VITE_DATA_MODE', 'typo')
  await expect(createDataClient()).rejects.toThrow('VITE_DATA_MODE')
})
