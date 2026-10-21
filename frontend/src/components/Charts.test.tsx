import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import Charts from './Charts'
import fixtures from '../mocks/fixtures.json'
import { snapshotSchema } from '../api/contracts'

it('keeps arc colors matched to legend colors when credits have no arc', () => {
  const snapshot = snapshotSchema.parse(structuredClone(fixtures.runs[0]))
  snapshot.services = [
    { name: 'Compute', amount: 100, percentage: 71.4 },
    { name: 'Credit', amount: -10, percentage: 0 },
    { name: 'Storage', amount: 50, percentage: 35.7 },
  ]
  const view = render(<Charts snapshot={snapshot} />)
  const arc = view.container.querySelectorAll('.recharts-pie-sector path')[1]
  const legend = screen.getByText('Storage').closest('li')!.querySelector('i')!
  expect(arc).toBeTruthy()
  const normalized = document.createElement('i')
  normalized.style.backgroundColor = arc!.getAttribute('fill')!
  expect(legend.style.backgroundColor).toBe(normalized.style.backgroundColor)
})
it('distinguishes normalized visible slices from snapshot percentages', () => {
  const snapshot = snapshotSchema.parse(structuredClone(fixtures.runs[0]))
  render(<Charts snapshot={snapshot} services={[snapshot.services[0]!]} />)
  expect(
    screen.getByText('Distribuição dos serviços visíveis'),
  ).toBeInTheDocument()
  expect(
    screen.getByText(
      'Anel: custos positivos visíveis · legenda: % do total do snapshot',
    ),
  ).toBeInTheDocument()
})
