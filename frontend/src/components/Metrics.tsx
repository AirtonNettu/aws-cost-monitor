import { ArrowUpRight, Bell, Layers3, Wallet } from 'lucide-react'
import type { Snapshot } from '../api/contracts'
import { money, percent, date } from '../lib/format'
import { useOptionalApp } from '../app/context'

export function BudgetIndicator({ snapshot }: { snapshot: Snapshot }) {
  const app = useOptionalApp()
  const currency = app?.currency ?? 'USD'
  const currentCost = snapshot.summary.total_cost
  const budgetMonthly = currency === 'BRL' ? 85000 : 15000
  const costAdjusted = currency === 'BRL' ? currentCost * 5.75 : currentCost
  const percentage = Math.min(100, Math.max(0, (costAdjusted / budgetMonthly) * 100))
  const isHealthy = percentage <= 85

  return (
    <div className="budget-indicator-card">
      <div className="budget-header">
        <div className="budget-title">
          <span className={`status-dot ${isHealthy ? 'green' : 'amber'}`} />
          <strong>Termômetro de Orçamento Mensal</strong>
          <small>{isHealthy ? 'Gastos dentro da meta prevista' : 'Atenção: Consumo elevado'}</small>
        </div>
        <div className="budget-values">
          <span>Consumo: <strong>{percentage.toFixed(1)}%</strong></span>
          <span className="divider">·</span>
          <span>Teto: <strong>{currency === 'BRL' ? 'R$ 85.000,00' : '$15,000.00'}</strong></span>
        </div>
      </div>
      <div className="budget-progress-track">
        <div
          className={`budget-progress-fill ${isHealthy ? 'fill-green' : 'fill-amber'}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

export function Metrics({ snapshot }: { snapshot: Snapshot }) {
  const app = useOptionalApp()
  const currency = app?.currency ?? 'USD'
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
        <strong>{money(summary.total_cost, currency)}</strong>
        <span>{currency} · período selecionado</span>
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
        <span>Inclui recomendações ativas</span>
      </article>
    </div>
  )
}
export function Comparison({ snapshot }: { snapshot: Snapshot }) {
  const app = useOptionalApp()
  const currency = app?.currency ?? 'USD'
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
        <strong>{money(comparison.previous_total, currency)}</strong>
        <small>
          {date(comparison.previous_period.start)} →{' '}
          {date(comparison.previous_period.end)}
        </small>
      </div>
      <span className="muted">→</span>
      <div>
        <span>Período atual</span>
        <strong>{money(comparison.current_total, currency)}</strong>
        <small>
          {date(snapshot.period.start)} → {date(snapshot.period.end)}
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
