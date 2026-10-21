import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { Metrics, Comparison } from './Metrics'
import fixtures from '../mocks/fixtures.json'
import { snapshotSchema } from '../api/contracts'

it('preserves zero variation and never infers variation for unequal periods', () => {
  const snapshot = snapshotSchema.parse(structuredClone(fixtures.runs[0]))
  snapshot.comparison!.variation = 0
  const view = render(<Metrics snapshot={snapshot} />)
  expect(screen.getByText('0%')).toBeInTheDocument()
  snapshot.comparison!.equivalent_periods = false
  view.rerender(
    <>
      <Metrics snapshot={snapshot} />
      <Comparison snapshot={snapshot} />
    </>,
  )
  expect(screen.getByText('Comparação indisponível')).toBeInTheDocument()
  expect(screen.queryByText('0%')).not.toBeInTheDocument()
  expect(screen.getByText(/Períodos não equivalentes/)).toBeInTheDocument()
})
it('renders unavailable base-zero comparison without calculating a percentage', () => {
  const snapshot = snapshotSchema.parse(structuredClone(fixtures.runs[0]))
  snapshot.comparison!.previous_total = 0
  snapshot.comparison!.variation = null
  render(
    <>
      <Metrics snapshot={snapshot} />
      <Comparison snapshot={snapshot} />
    </>,
  )
  expect(screen.getByText('Comparação indisponível')).toBeInTheDocument()
  expect(screen.getByText(/base anterior zero/)).toBeInTheDocument()
})
