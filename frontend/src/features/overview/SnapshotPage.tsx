import { lazy, Suspense, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, CalendarDays, CircleDot } from 'lucide-react'
import { useApp, useSnapshot } from '../../app/context'
import type { Snapshot } from '../../api/contracts'
import { date, dateTime } from '../../lib/format'
import { Metrics, Comparison } from '../../components/Metrics'
import { ErrorState, Loading, PageHeading } from '../../components/States'
import { ServiceTable } from '../../components/ServiceTable'
import { ExportReport } from '../../components/ExportReport'
import { Alerts } from '../alerts/Alerts'
import { AiPanel } from '../ai/AiPanel'
const Charts = lazy(() => import('../../components/Charts'))

const descriptions = {
  overview: [
    'Visão geral',
    'Uma visão clara dos seus custos. Decisões melhores para a sua nuvem.',
  ],
  costs: [
    'Análise de custos',
    'Explore serviços, acompanhe tendências e entenda a composição dos gastos.',
  ],
  alerts: [
    'Alertas FinOps',
    'Transforme os dados de custo em pontos de atenção para sua equipe.',
  ],
  ai: [
    'Analista IA',
    'Contexto para seus números, com interpretação desacoplada da análise financeira.',
  ],
} as const
export function SnapshotMeta({ snapshot }: { snapshot: Snapshot }) {
  return (
    <div className="snapshot-meta">
      <span>
        <CalendarDays size={14} aria-hidden="true" />
        {date(snapshot.period.start)} → {date(snapshot.period.end)}{' '}
        <small>(fim exclusivo)</small>
      </span>
      <span>Coleta: {dateTime(snapshot.collected_at)} BRT</span>
      {snapshot.estimated && (
        <span className="estimated">
          <CircleDot size={13} aria-hidden="true" />
          Valores estimados
        </span>
      )}
      {snapshot.source === 'mock' && (
        <span className="badge">Snapshot ilustrativo</span>
      )}
    </div>
  )
}
export function SnapshotContent({
  snapshot,
  kind = 'overview',
}: {
  snapshot: Snapshot
  kind?: keyof typeof descriptions
}) {
  const [service, setService] = useState('')
  const [search, setSearch] = useState('')
  const { client } = useApp()
  const services = snapshot.services.filter(
    (s) =>
      (!service || s.name === service) &&
      s.name
        .toLocaleLowerCase('pt-BR')
        .includes(search.toLocaleLowerCase('pt-BR')),
  )
  return (
    <>
      <SnapshotMeta snapshot={snapshot} />
      {(kind === 'overview' || kind === 'costs') && (
        <>
          <Metrics snapshot={snapshot} />
          <Suspense fallback={<div className="skeleton chart-skeleton" />}>
            <Charts snapshot={snapshot} services={services} />
          </Suspense>
          {kind === 'costs' && <Comparison snapshot={snapshot} />}
          <ServiceTable
            services={snapshot.services}
            compact={kind === 'overview'}
            service={service}
            setService={setService}
            search={search}
            setSearch={setSearch}
          />
        </>
      )}
      {kind === 'overview' && (
        <>
          <div className="section-link">
            <span>Entenda o que merece sua atenção</span>
            <Link to="/alerts">
              Ver todos os alertas <ArrowRight size={15} aria-hidden="true" />
            </Link>
          </div>
          <Alerts alerts={snapshot.alerts} compact />
          <div className="overview-ai">
            <div>
              <span className="eyebrow">INTELIGÊNCIA COM CONTEXTO</span>
              <h2>De números a decisões.</h2>
              <p>
                Conheça a interpretação do analista FinOps para este snapshot.
              </p>
            </div>
            <Link className="button accent" to="/ai">
              Explorar análise IA <ArrowRight size={16} aria-hidden="true" />
            </Link>
          </div>
        </>
      )}
      {kind === 'alerts' && <Alerts alerts={snapshot.alerts} />}
      {kind === 'ai' && (
        <AiPanel
          ai={snapshot.ai}
          simulated={client.mode === 'mock' || snapshot.source === 'mock'}
        />
      )}
    </>
  )
}
export function SnapshotPage({ kind }: { kind: keyof typeof descriptions }) {
  const query = useSnapshot()
  if (query.isPending) return <Loading />
  if (query.isError)
    return <ErrorState error={query.error} retry={() => void query.refetch()} />
  const [title, subtitle] = descriptions[kind]
  return (
    <>
      <PageHeading title={title} subtitle={subtitle}>
        <ExportReport snapshot={query.data} />
      </PageHeading>
      <SnapshotContent key={query.data.id} snapshot={query.data} kind={kind} />
    </>
  )
}
