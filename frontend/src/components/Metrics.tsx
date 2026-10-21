import { ArrowUpRight, Bell, Layers3, Wallet } from 'lucide-react'
import type { Snapshot } from '../api/contracts'
import { money, percent, date } from '../lib/format'

export function Metrics({ snapshot }: { snapshot: Snapshot }) {
  const { summary, comparison } = snapshot
  const comparable =
    comparison?.equivalent_periods && comparison.variation !== null
  return (
    <div className="metric-grid">
      <article
        className="metric-card primary-metric"
        data-testid="metric-total"
      >
        <div className="metric-label">
          Custo total AWS <Wallet size={18} aria-hidden="true" />
        </div>
        <strong>{money(summary.total_cost)}</strong>
        <span>USD · período selecionado</span>
      </article>
      <article className="metric-card">
        <div className="metric-label">
          Variação no período <ArrowUpRight size={18} aria-hidden="true" />
        </div>
        <strong
          className={
            comparable && comparison.variation! > 0 ? 'warning-text' : ''
          }
        >
          {comparable ? percent(comparison.variation!) : '—'}
        </strong>
        <span>
          {comparable
            ? 'vs. período equivalente anterior'
            : 'Comparação indisponível'}
        </span>
      </article>
      <article className="metric-card">
        <div className="metric-label">
          Maior serviço <Layers3 size={18} aria-hidden="true" />
        </div>
        <strong className="service-value">
          {summary.largest_service ?? 'Nenhum'}
        </strong>
        <span>
          {summary.largest_service_percentage !== null
            ? `${percent(summary.largest_service_percentage).replace('+', '')} do custo total`
            : 'Sem custos positivos'}
        </span>
      </article>
      <article className="metric-card">
        <div className="metric-label">
          Alertas FinOps <Bell size={18} aria-hidden="true" />
        </div>
        <strong>
          {summary.alert_count.toString().padStart(2, '0')}
          <small> alertas</small>
        </strong>
        <span>Inclui recomendações informativas</span>
      </article>
    </div>
  )
}
export function Comparison({ snapshot }: { snapshot: Snapshot }) {
  const comparison = snapshot.comparison
  if (!comparison)
    return <p className="notice">Não há períodos suficientes para comparar.</p>
  if (!comparison.equivalent_periods)
    return (
      <p className="notice">
        Períodos não equivalentes. A variação não é apresentada para evitar uma
        comparação incorreta.
      </p>
    )
  return (
    <div className="comparison-strip">
      <div>
        <span>Período anterior</span>
        <strong>{money(comparison.previous_total)}</strong>
        <small>
          {date(comparison.previous_period.start)} →{' '}
          {date(comparison.previous_period.end)} (fim exclusivo)
        </small>
      </div>
      <span className="muted">→</span>
      <div>
        <span>Período atual</span>
        <strong>{money(comparison.current_total)}</strong>
        <small>
          {date(snapshot.period.start)} → {date(snapshot.period.end)} (fim
          exclusivo)
        </small>
      </div>
      {comparison.variation === null && (
        <p>
          Variação indisponível: base anterior zero ou comparação não informada.
        </p>
      )}
    </div>
  )
}
