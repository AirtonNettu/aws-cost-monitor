import { describe, it, expect, vi } from 'vitest'
import { request } from './http'
import { z } from 'zod'
const schema = z.object({ value: z.number().finite() })
describe('HTTP boundary', () => {
  it('uses query-safe URLs and validates the response', async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response('{"value":12}'))
    expect(
      await request(
        'https://example.test/api/',
        'snapshots?tag=R%26D',
        schema,
        { fetcher },
      ),
    ).toEqual({ value: 12 })
    expect(String(fetcher.mock.calls[0]?.[0])).toBe(
      'https://example.test/api/snapshots?tag=R%26D',
    )
  })
  it('does not leak server error bodies', async () => {
    const fetcher = vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        new Response('private internal trace', { status: 500 }),
      )
    await expect(
      request('/api', 'snapshots', schema, { fetcher }),
    ).rejects.toThrow('Não foi possível carregar os dados (HTTP 500).')
  })
  it.each(['{"value":"12"}', '<html>invalid</html>'])(
    'rejects invalid payload %s',
    async (body) => {
      await expect(
        request('/api', 'snapshots', schema, {
          fetcher: vi.fn<typeof fetch>().mockResolvedValue(new Response(body)),
        }),
      ).rejects.toThrow('Resposta inválida')
    },
  )
  it('times out a request', async () => {
    const fetcher = vi.fn<typeof fetch>(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () =>
            reject(new DOMException('aborted', 'AbortError')),
          )
        }),
    )
    await expect(
      request('/api', 'snapshots', schema, { fetcher, timeout: 5 }),
    ).rejects.toThrow('O servidor demorou')
  })
  it('preserves caller cancellation', async () => {
    const controller = new AbortController()
    controller.abort()
    await expect(
      request('/api', 'snapshots', schema, { signal: controller.signal }),
    ).rejects.toMatchObject({ name: 'AbortError' })
  })
  it('reports network failures without exposing URLs', async () => {
    await expect(
      request('/api', 'snapshots', schema, {
        fetcher: vi
          .fn<typeof fetch>()
          .mockRejectedValue(new TypeError('private host')),
      }),
    ).rejects.toThrow('Não foi possível conectar ao backend.')
  })
})
