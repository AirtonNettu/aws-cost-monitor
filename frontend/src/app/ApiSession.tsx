import { useState, type FormEvent } from 'react'
import type { DataClient } from '../api/contracts'
import { createApiClient } from '../api/client'
import { App } from './App'

/** Mantém a autorização somente em memória e descarta o cache ao encerrar. */
export function ApiSession({ base }: { base: string }) {
  const [client, setClient] = useState<DataClient | null>(null)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function login(event: FormEvent) {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      const candidate = createApiClient(base, `Basic ${btoa(`${username}:${password}`)}`)
      await candidate.getHistory()
      setClient(candidate)
      setPassword('')
    } catch { setError('Acesso recusado ou API indisponível. Verifique as credenciais e a conexão.') }
    finally { setBusy(false) }
  }
  if (client) return <><button className="button api-logout" onClick={() => { setClient(null); setPassword('') }}>Sair da API</button><App client={client} /></>
  return <main className="login-page"><section className="panel login-panel"><p className="eyebrow">AWS COST MONITOR · API LOCAL</p><h1>Acessar workspace</h1><p className="muted">Acesso de leitura para um operador. Nenhuma credencial AWS é solicitada.</p><form onSubmit={event => void login(event)}>
    <label>Usuário<input required autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} /></label>
    <label>Senha<input required type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} /></label>
    {error && <p role="alert">{error}</p>}<button className="button accent" disabled={busy}>{busy ? 'Verificando…' : 'Entrar'}</button>
  </form><p className="muted">Sessão mantida apenas em memória. Use TLS fora de loopback.</p></section></main>
}
