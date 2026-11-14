import { useState } from 'react'
import { ArrowDownUp, Search } from 'lucide-react'
import type { Snapshot } from '../api/contracts'
import { money } from '../lib/format'
import { useOptionalApp } from '../app/context'
import { Empty } from './States'

function getServiceBadge(name: string): { label: string; color: string } {
  const lower = name.toLowerCase()
  if (lower.includes('ec2') || lower.includes('compute'))
    return { label: 'EC2', color: '#ff9900' }
  if (lower.includes('s3') || lower.includes('storage'))
    return { label: 'S3', color: '#e05244' }
  if (lower.includes('rds') || lower.includes('database'))
    return { label: 'RDS', color: '#2563eb' }
  if (lower.includes('lambda'))
    return { label: 'LAM', color: '#f97316' }
  if (lower.includes('cloudfront'))
    return { label: 'CF', color: '#8b5cf6' }
  if (lower.includes('dynamodb'))
    return { label: 'DYN', color: '#0284c7' }
  return { label: 'AWS', color: '#64748b' }
}

export function ServiceTable({
  services,
  compact = false,
  service = '',
  setService,
  search = '',
  setSearch,
}: {
  services: Snapshot['services']
  compact?: boolean
  service?: string
  setService?: (value: string) => void
  search?: string
  setSearch?: (value: string) => void
}) {
  const app = useOptionalApp()
  const currency = app?.currency ?? 'USD'
  const [sort, setSort] = useState<'amount' | 'name'>('amount')
  const [ascending, setAscending] = useState(false)
  const rows = services
    .filter(
      (s) =>
        (!service || s.name === service) &&
        s.name
          .toLocaleLowerCase('pt-BR')
          .includes(search.toLocaleLowerCase('pt-BR')),
    )
    .sort(
      (a, b) =>
        (sort === 'amount'
          ? a.amount - b.amount
          : a.name.localeCompare(b.name)) * (ascending ? 1 : -1),
    )
  const order = (column: 'amount' | 'name') => {
    setSort(column)
    setAscending(sort === column ? !ascending : column === 'name')
  }
  return (
    <section className="panel service-panel">
      <div className="panel-heading">
        <div>
          <h2>Custos por serviço</h2>
          <p>Ranking de custos · valores em {currency}</p>
        </div>
        <span className="badge">{services.length} serviços</span>
      </div>
      {!compact && (
        <>
          <div className="table-filters">
            <label className="search-field">
              <Search size={16} aria-hidden="true" />
              <span className="sr-only">Pesquisar serviço</span>
              <input
                type="search"
                placeholder="Pesquisar serviço…"
                value={search}
                onChange={(e) => setSearch?.(e.target.value)}
              />
            </label>
            <label className="select-field">
              <span>Serviço</span>
              <select
                value={service}
                onChange={(e) => setService?.(e.target.value)}
              >
                <option value="">Todos os serviços</option>
                {services.map((s) => (
                  <option key={s.name}>{s.name}</option>
                ))}
              </select>
            </label>
          </div>
          <p className="filter-scope">
            Pesquisa e serviço filtram a tabela e a distribuição. KPIs, evolução
            e alertas mantêm o período/tag selecionados.
          </p>
        </>
      )}
      {!services.length ? (
        <Empty title="Sem serviços neste período">
          Altere o período ou confira a disponibilidade do snapshot.
        </Empty>
      ) : (
        <div className="table-scroll">
          <table aria-label="Custos por serviço">
            <thead>
              <tr>
                <th
                  aria-sort={
                    sort === 'name'
                      ? ascending
                        ? 'ascending'
                        : 'descending'
                      : 'none'
                  }
                >
                  <button onClick={() => order('name')}>
                    Serviço <ArrowDownUp size={13} aria-hidden="true" />
                  </button>
                </th>
                <th
                  aria-sort={
                    sort === 'amount'
                      ? ascending
                        ? 'ascending'
                        : 'descending'
                      : 'none'
                  }
                >
                  <button onClick={() => order('amount')}>
                    Custo total <ArrowDownUp size={13} aria-hidden="true" />
                  </button>
                </th>
                <th>Participação</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => {
                const badge = getServiceBadge(s.name)
                return (
                  <tr key={s.name}>
                    <td>
                      <span
                        className="service-badge"
                        style={{
                          backgroundColor: badge.color,
                          color: '#ffffff',
                          fontWeight: 700,
                          fontSize: '10px',
                          padding: '3px 7px',
                          borderRadius: '6px',
                          display: 'inline-block',
                          marginRight: '10px',
                          minWidth: '38px',
                          textAlign: 'center',
                          letterSpacing: '0.5px',
                        }}
                      >
                        {badge.label}
                      </span>
                      <strong>{s.name}</strong>
                    </td>
                    <td className="amount">{money(s.amount, currency)}</td>
                    <td>
                      <div className="share-cell">
                        <div className="share-track" aria-hidden="true">
                          <div
                            style={{
                              width: `${Math.min(100, Math.max(0, s.percentage))}%`,
                              backgroundColor: badge.color,
                            }}
                          />
                        </div>
                        <span>{s.percentage.toFixed(1)}%</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {!rows.length && (
            <Empty title="Nenhum serviço encontrado">
              Tente outro nome ou remova o filtro.
            </Empty>
          )}
        </div>
      )}
    </section>
  )
}
