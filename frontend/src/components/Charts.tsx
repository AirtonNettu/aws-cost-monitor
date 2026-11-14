import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { Snapshot } from '../api/contracts'
import { money } from '../lib/format'
import { useOptionalApp } from '../app/context'
import { Empty } from './States'

const AWS_PALETTE: Record<string, string> = {
  ec2: '#ff9900',
  compute: '#ff9900',
  s3: '#e05244',
  storage: '#e05244',
  rds: '#2563eb',
  database: '#2563eb',
  cloudfront: '#8b5cf6',
  lambda: '#f97316',
  dynamodb: '#0284c7',
  elasticache: '#059669',
  sns: '#ec4899',
  sqs: '#ea580c',
}

const fallbackColors = [
  '#ff9900',
  '#2563eb',
  '#e05244',
  '#8b5cf6',
  '#f97316',
  '#06b6d4',
  '#10b981',
  '#64748b',
]

function getServiceColor(name: string, index = 0): string {
  const lower = name.toLowerCase()
  for (const [key, color] of Object.entries(AWS_PALETTE)) {
    if (lower.includes(key)) return color
  }
  return fallbackColors[index % fallbackColors.length] ?? '#ff9900'
}

export default function Charts({
  snapshot,
  services = snapshot.services,
}: {
  snapshot: Snapshot
  services?: Snapshot['services']
}) {
  const app = useOptionalApp()
  const currency = app?.currency ?? 'USD'
  const serviceColors = new Map(
    snapshot.services.map((service, index) => [
      service.name,
      getServiceColor(service.name, index),
    ]),
  )
  return (
    <div className="chart-grid">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Evolução dos gastos</h2>
            <p>Custos diários do snapshot · USD</p>
          </div>
          <span className="badge">Diário</span>
        </div>
        {snapshot.timeline.length ? (
          <>
            <div
              className="chart-box"
              role="img"
              aria-label="Gráfico de evolução diária dos custos; valores na tabela expandível abaixo."
            >
              <ResponsiveContainer width="100%" height="100%" minWidth={1}>
                <AreaChart
                  data={snapshot.timeline}
                  margin={{ top: 12, right: 10, bottom: 0, left: 0 }}
                  accessibilityLayer
                >
                  <defs>
                    <linearGradient
                      id="cost-gradient"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="0%"
                        stopColor="#ff9900"
                        stopOpacity={0.4}
                      />
                      <stop
                        offset="100%"
                        stopColor="#ff9900"
                        stopOpacity={0.02}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid
                    vertical={false}
                    stroke="var(--border)"
                    strokeDasharray="4 4"
                  />
                  <XAxis
                    dataKey="date"
                    tickFormatter={(v) =>
                      String(v).slice(5).split('-').reverse().join('/')
                    }
                    minTickGap={34}
                    tickLine={false}
                    axisLine={false}
                    stroke="var(--muted)"
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    tickFormatter={(v) => (currency === 'BRL' ? `R$${v}` : `$${v}`)}
                    width={64}
                    tickLine={false}
                    axisLine={false}
                    stroke="var(--muted)"
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--surface)',
                      borderColor: 'var(--border)',
                      borderRadius: 10,
                      color: 'var(--text)',
                    }}
                    formatter={(v) => money(Number(v), currency)}
                  />
                  <Area
                    type="monotone"
                    dataKey="amount"
                    name="Custo"
                    stroke="#ff9900"
                    strokeWidth={2.5}
                    fill="url(#cost-gradient)"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <details className="chart-data">
              <summary>Ver dados diários em tabela</summary>
              <div className="table-scroll">
                <table aria-label="Custos diários">
                  <thead>
                    <tr>
                      <th>Data</th>
                      <th>Custo USD</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshot.timeline.map((point) => (
                      <tr key={point.date}>
                        <td>{point.date}</td>
                        <td>{money(point.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </>
        ) : (
          <Empty title="Sem série temporal">
            Série temporal não disponível neste snapshot.
          </Empty>
        )}
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Distribuição dos serviços visíveis</h2>
            <p>
              Anel: custos positivos visíveis · legenda: % do total do snapshot
            </p>
          </div>
        </div>
        {services.some((service) => service.amount > 0) ? (
          <>
            <div
              className="donut-box"
              role="img"
              aria-label="Gráfico de distribuição; custos e percentuais na legenda abaixo."
            >
              <ResponsiveContainer width="100%" height="100%" minWidth={1}>
                <PieChart accessibilityLayer>
                  <Pie
                    data={services.filter((s) => s.amount > 0)}
                    dataKey="amount"
                    nameKey="name"
                    innerRadius={60}
                    outerRadius={84}
                    paddingAngle={4}
                    cornerRadius={4}
                    stroke="none"
                    isAnimationActive={false}
                  >
                    {services
                      .filter((s) => s.amount > 0)
                      .map((service) => (
                        <Cell
                          key={service.name}
                          fill={serviceColors.get(service.name)}
                        />
                      ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: 'var(--surface)',
                      borderColor: 'var(--border)',
                      borderRadius: 10,
                    }}
                    formatter={(v) => money(Number(v), currency)}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ul className="chart-legend">
              {services.map((service) => (
                <li key={service.name}>
                  <span>
                    <i
                      style={{ background: serviceColors.get(service.name) }}
                    />
                    {service.name}
                  </span>
                  <strong>
                    {service.percentage.toFixed(1)}%
                    <small>{money(service.amount, currency)}</small>
                  </strong>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <Empty title="Sem distribuição">
            Nenhum custo positivo disponível.
          </Empty>
        )}
      </section>
    </div>
  )
}
