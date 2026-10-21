import { useState } from 'react'
import { Download } from 'lucide-react'
import type { ReportFormat, Snapshot } from '../api/contracts'
import { useApp } from '../app/context'

export function ExportReport({ snapshot }: { snapshot: Snapshot }) {
  const { client } = useApp()
  const [selected, setSelected] = useState<ReportFormat | ''>('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const format = snapshot.report_formats.includes(selected as ReportFormat)
    ? (selected as ReportFormat)
    : snapshot.report_formats[0]
  const available =
    client.mode === 'api' && snapshot.source !== 'mock' && !!format
  const download = async () => {
    if (!available || !format) return
    setBusy(true)
    setError('')
    try {
      const blob = await client.exportReport(snapshot.id, format)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `aws-cost-report.${format === 'markdown' ? 'md' : format}`
      document.body.append(link)
      link.click()
      link.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Não foi possível exportar o relatório.',
      )
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="export-control">
      {available && (
        <label className="sr-label">
          Formato
          <select
            aria-label="Formato de exportação"
            value={format}
            onChange={(e) => setSelected(e.target.value as ReportFormat)}
          >
            {snapshot.report_formats.map((value) => (
              <option key={value}>{value}</option>
            ))}
          </select>
        </label>
      )}
      <button
        className="button"
        disabled={!available || busy}
        onClick={() => void download()}
        aria-describedby={!available ? 'export-note' : undefined}
      >
        <Download size={16} aria-hidden="true" />
        {busy ? 'Exportando…' : 'Exportar relatório'}
      </button>
      {!available && (
        <small id="export-note">Disponível após integração com o backend</small>
      )}
      {error && <p role="alert">{error}</p>}
    </div>
  )
}
