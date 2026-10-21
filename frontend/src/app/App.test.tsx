import { describe, it, expect, vi } from 'vitest'
import { render, screen, within, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { App } from './App'
import { createMockClient } from '../mocks/adapter'
import type { DataClient } from '../api/contracts'

function mount(
  path = '/',
  client: DataClient = createMockClient('success', 0),
) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App client={client} />
    </MemoryRouter>,
  )
}
describe('dashboard flows', () => {
  it('identifies simulated data and presents backend KPIs and estimated periods', async () => {
    mount()
    expect(await screen.findByText('Dados simulados')).toBeInTheDocument()
    expect(
      await screen.findByRole('heading', { name: 'Visão geral' }),
    ).toBeInTheDocument()
    const total = await screen.findByTestId('metric-total')
    expect(total).toHaveTextContent('12.207,50')
    expect(screen.getByText('Valores estimados')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Exportar relatório' }),
    ).toBeDisabled()
  })
  it('navigates all sections and toggles the persisted theme', async () => {
    const user = userEvent.setup()
    mount()
    await user.click(
      await screen.findByRole('link', { name: 'Alertas FinOps' }),
    )
    expect(
      await screen.findByRole('heading', { name: 'Alertas FinOps' }),
    ).toBeInTheDocument()
    await user.click(screen.getByRole('link', { name: 'Analista IA' }))
    expect(
      await screen.findByRole('heading', { name: 'Analista IA' }),
    ).toBeInTheDocument()
    expect(await screen.findByText('Resumo executivo')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Ativar tema claro' }))
    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    await user.click(screen.getByRole('button', { name: 'Ativar tema escuro' }))
  })
  it('filters the displayed services without changing financial KPIs', async () => {
    const user = userEvent.setup()
    mount('/costs')
    const search = await screen.findByRole('searchbox', {
      name: 'Pesquisar serviço',
    })
    await user.type(search, 'Amazon S3')
    const table = screen.getByRole('table', { name: 'Custos por serviço' })
    expect(within(table).getByText('Amazon S3')).toBeInTheDocument()
    expect(within(table).queryByText('Amazon EC2')).not.toBeInTheDocument()
    expect(screen.getByTestId('metric-total')).toHaveTextContent('12.207,50')
    await user.clear(search)
    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Serviço' }),
      'Amazon RDS',
    )
    expect(within(table).queryByText('Amazon S3')).not.toBeInTheDocument()
  })
  it('fetches a new complete snapshot when period or tag changes', async () => {
    const user = userEvent.setup()
    mount()
    await user.selectOptions(
      await screen.findByRole('combobox', { name: 'Período' }),
      '7',
    )
    await waitFor(() =>
      expect(screen.getByTestId('metric-total')).toHaveTextContent('2.859,50'),
    )
    await user.selectOptions(
      screen.getByRole('combobox', { name: 'Tag' }),
      'Environment: Production',
    )
    await waitFor(() =>
      expect(screen.getByTestId('metric-total')).toHaveTextContent('2.001,62'),
    )
  })
  it('recovers from request errors and shows a useful loading state', async () => {
    const user = userEvent.setup()
    const client = createMockClient('success', 0)
    const original = client.getSnapshot
    client.getSnapshot = vi
      .fn()
      .mockRejectedValueOnce(new Error('Backend indisponível'))
      .mockImplementation(original)
    mount('/', client)
    expect(
      screen.getByRole('status', { name: 'Carregando análise' }),
    ).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Backend indisponível',
    )
    await user.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(await screen.findByTestId('metric-total')).toHaveTextContent(
      '12.207,50',
    )
  })
  it('handles empty data and absent comparison without invented values', async () => {
    mount('/', createMockClient('empty', 0))
    expect(
      await screen.findByText('Sem serviços neste período'),
    ).toBeInTheDocument()
    expect(screen.getByText('Comparação indisponível')).toBeInTheDocument()
  })
  it.each(['ai-unavailable', 'ai-processing'])(
    'keeps AI %s separate from cost data',
    async (scenario) => {
      mount('/ai', createMockClient(scenario, 0))
      expect(
        await screen.findByText(
          scenario === 'ai-processing'
            ? 'Análise em processamento'
            : 'IA indisponível',
        ),
      ).toBeInTheDocument()
    },
  )
  it('opens historical runs and compares two supplied totals side by side', async () => {
    const user = userEvent.setup()
    mount('/history')
    const checks = await screen.findAllByRole('checkbox')
    await user.click(checks[0]!)
    await user.click(checks[1]!)
    expect(
      screen.getByRole('region', { name: 'Comparação de execuções' }),
    ).toBeInTheDocument()
    await user.click(screen.getAllByRole('link', { name: 'Abrir análise' })[0]!)
    expect(
      await screen.findByRole('heading', { name: 'Análise histórica' }),
    ).toBeInTheDocument()
    expect(
      await screen.findByText('Série temporal não disponível neste snapshot.'),
    ).toBeInTheDocument()
  })
  it('shows an empty history and a useful 404 page', async () => {
    const view = mount('/history', createMockClient('empty', 0))
    expect(await screen.findByText('Nenhuma análise salva')).toBeInTheDocument()
    view.unmount()
    mount('/unknown')
    expect(
      await screen.findByRole('heading', { name: 'Página não encontrada' }),
    ).toBeInTheDocument()
  })
})

it('sorts and searches service rows and filters alert severity', async () => {
  const user = userEvent.setup()
  mount('/costs')
  await screen.findByRole('heading', { name: 'Análise de custos' })
  await user.click(screen.getByRole('button', { name: 'Custo total' }))
  const table = screen.getByRole('table', { name: 'Custos por serviço' })
  expect(within(table).getAllByRole('row')[1]).toHaveTextContent(
    'Outros serviços',
  )
  await user.click(screen.getByRole('button', { name: 'Serviço' }))
  expect(within(table).getAllByRole('row')[1]).toHaveTextContent(
    'Amazon CloudFront',
  )
  await user.type(screen.getByRole('searchbox'), 'does not exist')
  expect(screen.getByText('Nenhum serviço encontrado')).toBeInTheDocument()
  await user.click(screen.getByRole('link', { name: 'Alertas FinOps' }))
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Severidade' }),
    'critical',
  )
  expect(screen.getByText('Nenhum alerta nesta severidade')).toBeInTheDocument()
})
it('limits history comparison to two runs and allows deselecting', async () => {
  const user = userEvent.setup()
  mount('/history')
  const checks = await screen.findAllByRole('checkbox')
  await user.click(checks[0]!)
  await user.click(checks[1]!)
  expect(checks[2]).toBeDisabled()
  await user.click(checks[0]!)
  expect(checks[2]).not.toBeDisabled()
  expect(
    screen.queryByRole('region', { name: 'Comparação de execuções' }),
  ).not.toBeInTheDocument()
})
it('shows a historical detail error without losing navigation', async () => {
  mount('/history/missing')
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Execução não encontrada',
  )
  expect(screen.getByRole('link', { name: 'Histórico' })).toBeInTheDocument()
})
it('moves keyboard focus into the mobile navigation and closes it with Escape', async () => {
  const user = userEvent.setup()
  mount('/alerts')
  const open = screen.getByRole('button', { name: 'Abrir menu' })
  await user.click(open)
  expect(screen.getByRole('link', { name: 'Visão geral' })).toHaveFocus()
  await user.keyboard('{Escape}')
  expect(screen.getByRole('button', { name: 'Abrir menu' })).toHaveFocus()
  expect(open).toHaveAttribute('aria-expanded', 'false')
})
