import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { ExportReport } from './ExportReport'
import { AppContext } from '../app/context'
import { createMockClient } from '../mocks/adapter'
import { snapshotSchema } from '../api/contracts'
import fixtures from '../mocks/fixtures.json'

it('downloads only the format advertised by the API and reports download failure', async () => {
  const user = userEvent.setup()
  const snapshot = snapshotSchema.parse(structuredClone(fixtures.runs[0]))
  snapshot.source = 'aws'
  snapshot.report_formats = ['json', 'markdown']
  const client = createMockClient('success', 0)
  client.mode = 'api'
  client.exportReport = vi
    .fn()
    .mockResolvedValueOnce(new Blob(['report']))
    .mockRejectedValueOnce(new Error('Exportação indisponível'))
  const createUrl = vi.fn().mockReturnValue('blob:report')
  Object.defineProperty(URL, 'createObjectURL', {
    value: createUrl,
    configurable: true,
  })
  Object.defineProperty(URL, 'revokeObjectURL', {
    value: vi.fn(),
    configurable: true,
  })
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(() => {})
  render(
    <AppContext.Provider
      value={{ client, filters: { days: 30, tag: '' }, setFilters: () => {} }}
    >
      <ExportReport snapshot={snapshot} />
    </AppContext.Provider>,
  )
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Formato de exportação' }),
    'markdown',
  )
  await user.click(screen.getByRole('button', { name: 'Exportar relatório' }))
  await waitFor(() => expect(click).toHaveBeenCalledOnce())
  expect(client.exportReport).toHaveBeenCalledWith(snapshot.id, 'markdown')
  expect(createUrl).toHaveBeenCalledOnce()
  await user.click(screen.getByRole('button', { name: 'Exportar relatório' }))
  expect(await screen.findByRole('alert')).toHaveTextContent(
    'Exportação indisponível',
  )
})
