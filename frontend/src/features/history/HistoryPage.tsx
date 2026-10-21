import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight, GitCompareArrows } from 'lucide-react'
import { useApp } from '../../app/context'
import { money, dateTime, date } from '../../lib/format'
import {
  Empty,
  ErrorState,
  Loading,
  PageHeading,
} from '../../components/States'
import { SnapshotContent } from '../overview/SnapshotPage'
import { ExportReport } from '../../components/ExportReport'

export function HistoryPage() {
  const { client } = useApp()
  const [selected, setSelected] = useState<string[]>([])
  const query = useQuery({
    queryKey: ['history', client.mode],
    queryFn: ({ signal }) => client.getHistory(signal),
  })
  if (query.isPending) return <Loading />
  if (query.isError)
    return <ErrorState error={query.error} retry={() => void query.refetch()} />
  const runs = query.data.runs
  const compared = runs.filter((run) => selected.includes(run.id))
  return (
    <>
      <PageHeading
        title="Histórico de análises"
        subtitle="Cada coleta, um registro. Explore a evolução dos seus snapshots."
      />
      {!runs.length ? (
        <section className="panel">
          <Empty title="Nenhuma análise salva">
            O histórico aparecerá após o backend disponibilizar snapshots
            persistidos.
          </Empty>
        </section>
      ) : (
        <>
          <div className="history-intro">
            <GitCompareArrows size={20} aria-hidden="true" />
            <div>
              <strong>Compare seus registros</strong>
              <p>
                Selecione até duas execuções para visualizar os valores lado a
                lado.
              </p>
            </div>
            <span className="badge">{selected.length}/2 selecionadas</span>
          </div>
          {compared.length === 2 && (
            <section
              className="comparison-panel panel"
              aria-label="Comparação de execuções"
            >
              <h2>Comparação de execuções</h2>
              <p className="muted">
                Totais de cada snapshot. Intervalos podem se sobrepor; nenhuma
                variação entre execuções foi calculada.
              </p>
              <div className="history-comparison">
                {compared.map((run) => (
                  <article key={run.id}>
                    <span>Coleta em {dateTime(run.collected_at)} BRT</span>
                    <strong>{money(run.total_cost)}</strong>
                    <p>
                      {date(run.period.start)} → {date(run.period.end)} (fim
                      exclusivo)
                    </p>
                    <p>Maior serviço: {run.largest_service ?? 'Nenhum'}</p>
                  </article>
                ))}
              </div>
            </section>
          )}
          <section className="panel">
            <div className="table-scroll">
              <table aria-label="Histórico de análises">
                <thead>
                  <tr>
                    <th>Comparar</th>
                    <th>Data da coleta (BRT)</th>
                    <th>Período (fim exclusivo)</th>
                    <th>Custo total USD</th>
                    <th>Status</th>
                    <th>
                      <span className="sr-only">Ações</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.id}>
                      <td>
                        <input
                          type="checkbox"
                          aria-label={`Comparar coleta de ${dateTime(run.collected_at)}`}
                          checked={selected.includes(run.id)}
                          disabled={
                            selected.length >= 2 && !selected.includes(run.id)
                          }
                          onChange={(e) =>
                            setSelected(
                              e.target.checked
                                ? [...selected, run.id]
                                : selected.filter((id) => id !== run.id),
                            )
                          }
                        />
                      </td>
                      <td>{dateTime(run.collected_at)}</td>
                      <td>
                        {date(run.period.start)} → {date(run.period.end)}
                      </td>
                      <td className="amount">{money(run.total_cost)}</td>
                      <td>
                        <span className="badge">
                          {run.estimated ? 'Estimado' : 'Consolidado'}
                        </span>
                      </td>
                      <td>
                        <Link
                          className="text-link"
                          to={`/history/${encodeURIComponent(run.id)}`}
                        >
                          Abrir análise{' '}
                          <ArrowUpRight size={15} aria-hidden="true" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </>
  )
}
export function HistoryDetail() {
  const { client } = useApp()
  const { runId = '' } = useParams()
  const query = useQuery({
    queryKey: ['run', client.mode, runId],
    queryFn: ({ signal }) => client.getRun(runId, signal),
  })
  if (query.isPending) return <Loading />
  if (query.isError)
    return <ErrorState error={query.error} retry={() => void query.refetch()} />
  return (
    <>
      <Link to="/history" className="back-link">
        <ArrowLeft size={16} aria-hidden="true" />
        Voltar ao histórico
      </Link>
      <PageHeading
        title="Análise histórica"
        subtitle="Um retrato dos custos no momento da coleta. Os filtros atuais não se aplicam."
      >
        <ExportReport snapshot={query.data} />
      </PageHeading>
      <SnapshotContent key={query.data.id} snapshot={query.data} kind="costs" />
    </>
  )
}
