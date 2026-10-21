import { useState } from 'react'
import { ArrowDownUp, Search } from 'lucide-react'
import type { Snapshot } from '../api/contracts'
import { money } from '../lib/format'
import { Empty } from './States'

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
          <p>Ranking de custos · valores em USD</p>
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
              {rows.map((s, i) => (
                <tr key={s.name}>
                  <td>
                    <span className="service-initial">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    {s.name}
                  </td>
                  <td className="amount">{money(s.amount)}</td>
                  <td>
                    <div className="share-cell">
                      <div className="share-track" aria-hidden="true">
                        <div
                          style={{
                            width: `${Math.min(100, Math.max(0, s.percentage))}%`,
                          }}
                        />
                      </div>
                      <span>{s.percentage.toFixed(1)}%</span>
                    </div>
                  </td>
                </tr>
              ))}
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
