import type { z } from 'zod'

interface Options { signal?: AbortSignal; timeout?: number; fetcher?: typeof fetch }

/** All requests are reads of saved snapshots; never triggers an AWS collection. */
export async function fetchResponse(base: string, path: string, options: Options = {}): Promise<Response> {
  const controller = new AbortController()
  let timedOut = false
  const abort = () => controller.abort()
  if (options.signal?.aborted) throw new DOMException('Cancelado', 'AbortError')
  options.signal?.addEventListener('abort', abort, { once: true })
  const timer = setTimeout(() => { timedOut = true; controller.abort() }, options.timeout ?? 15_000)
  try {
    const url = `${base.replace(/\/$/, '')}/${path.replace(/^\//, '')}`
    const response = await (options.fetcher ?? fetch)(url, {
      signal: controller.signal, headers: { Accept: 'application/json' }, credentials: 'same-origin',
    })
    if (!response.ok) throw new Error(`Não foi possível carregar os dados (HTTP ${response.status}).`)
    // Read body inside the timeout, including slow/streamed responses.
    const body = await response.arrayBuffer()
    return new Response(body, { status: response.status, headers: response.headers })
  } catch (error) {
    if (options.signal?.aborted) throw new DOMException('Cancelado', 'AbortError')
    if (timedOut) throw new Error('O servidor demorou para responder. Tente novamente.')
    if (error instanceof TypeError) throw new Error('Não foi possível conectar ao backend.')
    throw error
  } finally {
    clearTimeout(timer)
    options.signal?.removeEventListener('abort', abort)
  }
}

export async function request<T>(base: string, path: string, schema: z.ZodType<T>, options: Options = {}): Promise<T> {
  const response = await fetchResponse(base, path, options)
  try {
    return schema.parse(await response.json())
  } catch {
    throw new Error('Resposta inválida do backend. Confira o contrato da API.')
  }
}
