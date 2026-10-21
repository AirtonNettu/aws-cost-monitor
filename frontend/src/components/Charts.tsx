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
import { Empty } from './States'

const colors = [
  '#44d7a3',
  '#8394fa',
  '#efbc70',
  '#59b6e7',
  '#d59be8',
  '#91a59b',
]
export default function Charts({
  snapshot,
  services = snapshot.services,
}: {
  snapshot: Snapshot
  services?: Snapshot['services']
}) {
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
                        stopColor="#44d7a3"
                        stopOpacity={0.35}
                      />
                      <stop
                        offset="100%"
                        stopColor="#44d7a3"
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
                    tickFormatter={(v) => `$${v}`}
                    width={58}
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
                    formatter={(v) => money(Number(v))}
                  />
                  <Area
                    type="monotone"
                    dataKey="amount"
                    name="Custo"
                    stroke="#44d7a3"
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
            <h2>Distribuição por serviço</h2>
            <p>Participações fornecidas pelo snapshot</p>
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
                      .map((service, i) => (
                        <Cell
                          key={service.name}
                          fill={colors[i % colors.length]}
                        />
                      ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: 'var(--surface)',
                      borderColor: 'var(--border)',
                      borderRadius: 10,
                    }}
                    formatter={(v) => money(Number(v))}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <ul className="chart-legend">
              {services.map((service, i) => (
                <li key={service.name}>
                  <span>
                    <i style={{ background: colors[i % colors.length] }} />
                    {service.name}
                  </span>
                  <strong>
                    {service.percentage.toFixed(1)}%
                    <small>{money(service.amount)}</small>
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
