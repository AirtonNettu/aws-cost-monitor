import { it, expect, vi } from 'vitest'
import { createMockClient } from './adapter'
import { snapshotSchema } from '../api/contracts'

it('returns precomputed period and tag snapshots without network calls', async () => {
  const network = vi.spyOn(globalThis, 'fetch')
  const client = createMockClient('success', 0)
  const snapshot = await client.getSnapshot({
    days: 7,
    tag: 'Environment: Production',
  })
  expect(snapshot.source).toBe('mock')
  expect(snapshot.tag).toBe('Environment: Production')
  expect(snapshot.period).toEqual({ start: '2026-10-13', end: '2026-10-20' })
  expect(snapshot.summary.total_cost).toBe(2001.62)
  expect(network).not.toHaveBeenCalled()
})
it('rejects malformed financial data instead of coercing values', async () => {
  const snapshot = await createMockClient('success', 0).getSnapshot({
    days: 30,
    tag: '',
  })
  expect(
    snapshotSchema.safeParse({
      ...snapshot,
      summary: { ...snapshot.summary, total_cost: '100' },
    }).success,
  ).toBe(false)
})
it('supports empty, error and unavailable AI scenarios', async () => {
  const empty = await createMockClient('empty', 0).getSnapshot({
    days: 30,
    tag: '',
  })
  expect(empty.services).toHaveLength(0)
  expect(empty.comparison).toBeNull()
  expect(
    (
      await createMockClient('ai-unavailable', 0).getSnapshot({
        days: 30,
        tag: '',
      })
    ).ai.status,
  ).toBe('unavailable')
  expect(
    (
      await createMockClient('ai-processing', 0).getSnapshot({
        days: 30,
        tag: '',
      })
    ).ai.status,
  ).toBe('processing')
  await expect(createMockClient('error', 0).getHistory()).rejects.toThrow(
    'simulada',
  )
})
it('serves history details, rejects missing runs and does not offer fake exports', async () => {
  const client = createMockClient('success', 0)
  const history = await client.getHistory()
  expect(history.runs).toHaveLength(4)
  const snapshot = await client.getRun(history.runs[0]!.id)
  expect(snapshot.timeline).toEqual([])
  expect(snapshot.ai.model).toBeNull()
  await expect(client.getRun('missing')).rejects.toThrow('não encontrada')
  await expect(client.exportReport('demo', 'csv')).rejects.toThrow('backend')
})
it('supports cancellation and rejects unknown scenarios', async () => {
  expect(() => createMockClient('typo')).toThrow('Cenário')
  const controller = new AbortController()
  const pending = createMockClient('success', 500).getSnapshot(
    { days: 30, tag: '' },
    controller.signal,
  )
  controller.abort()
  await expect(pending).rejects.toMatchObject({ name: 'AbortError' })
})
