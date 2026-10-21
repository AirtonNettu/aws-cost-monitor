import { useState } from 'react'
import {
  AlertTriangle,
  ArrowUpRight,
  CircleCheck,
  Info,
  Layers3,
} from 'lucide-react'
import type { Snapshot } from '../../api/contracts'
import { Empty } from '../../components/States'

const titles = {
  growth: 'Crescimento acima do limiar',
  concentration: 'Concentração de despesas',
  top_services: 'Ranking de serviços',
  untagged: 'Recursos sem tag',
}
const labels = { info: 'Informativo', warning: 'Atenção', critical: 'Crítico' }
export function Alerts({
  alerts,
  compact = false,
}: {
  alerts: Snapshot['alerts']
  compact?: boolean
}) {
  const [severity, setSeverity] = useState('')
  const visible = alerts.filter((a) => !severity || a.severity === severity)
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>{compact ? 'Pontos de atenção' : 'Central de alertas'}</h2>
          <p>Regras determinísticas aplicadas pelo Python</p>
        </div>
        {!compact && (
          <label className="select-field">
            <span>Severidade</span>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
            >
              <option value="">Todas</option>
              <option value="warning">Atenção</option>
              <option value="info">Informativo</option>
              <option value="critical">Crítico</option>
            </select>
          </label>
        )}
      </div>
      {!visible.length ? (
        <Empty
          title={
            alerts.length
              ? 'Nenhum alerta nesta severidade'
              : 'Nenhum alerta neste período'
          }
        >
          Os alertas dependem dos dados e limites definidos no backend.
        </Empty>
      ) : (
        <div className="alert-list">
          {visible.map((alert) => (
            <article key={alert.id} className={`alert-card ${alert.severity}`}>
              <div className="alert-icon">
                {alert.type === 'growth' ? (
                  <ArrowUpRight size={20} />
                ) : alert.type === 'concentration' ? (
                  <Layers3 size={20} />
                ) : alert.severity === 'info' ? (
                  <Info size={20} />
                ) : (
                  <AlertTriangle size={20} />
                )}
              </div>
              <div>
                <div className="alert-title">
                  <h3>{titles[alert.type]}</h3>
                  <span className={`severity ${alert.severity}`}>
                    {labels[alert.severity]}
                  </span>
                </div>
                <p>{alert.message}</p>
              </div>
            </article>
          ))}
        </div>
      )}
      {!compact && (
        <p className="panel-footnote">
          <CircleCheck size={15} aria-hidden="true" />
          Crescimento por limiar não representa detecção estatística de
          anomalias. Essa análise está planejada.
        </p>
      )}
    </section>
  )
}
