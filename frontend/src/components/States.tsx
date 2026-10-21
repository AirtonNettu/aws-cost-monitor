import { AlertCircle, Database, RefreshCw } from 'lucide-react'
import type { ReactNode } from 'react'

export function Loading() {
  return (
    <div className="loading" role="status" aria-label="Carregando análise">
      <span className="sr-only">Carregando análise…</span>
      <div className="skeleton title-skeleton" />
      <div className="metric-grid">
        {[1, 2, 3, 4].map((n) => (
          <div className="skeleton card-skeleton" key={n} />
        ))}
      </div>
      <div className="skeleton chart-skeleton" />
    </div>
  )
}
export function Empty({
  title,
  children,
}: {
  title: string
  children?: ReactNode
}) {
  return (
    <div className="empty-state">
      <Database size={28} aria-hidden="true" />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  )
}
export function ErrorState({
  error,
  retry,
}: {
  error: Error
  retry: () => void
}) {
  return (
    <section role="alert" className="error-state">
      <AlertCircle aria-hidden="true" />
      <h2>Não foi possível carregar a análise</h2>
      <p>{error.message}</p>
      <button className="button" onClick={retry}>
        <RefreshCw size={16} aria-hidden="true" />
        Tentar novamente
      </button>
    </section>
  )
}
export function PageHeading({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle: string
  children?: ReactNode
}) {
  return (
    <div className="page-heading">
      <div>
        <p className="eyebrow">WORKSPACE / FINOPS</p>
        <h1 tabIndex={-1} id="page-title">
          {title}
        </h1>
        <p className="muted">{subtitle}</p>
      </div>
      {children}
    </div>
  )
}
