import { describe, expect, it } from 'vitest'
import { historySchema, snapshotSchema } from './contracts'
import fixtures from '../mocks/fixtures.json'

describe('Contratos da API — Validação Zod', () => {
  it('valida com sucesso todas as fixtures de snapshots sintéticos', () => {
    for (const [key, rawSnapshot] of Object.entries(fixtures.snapshots)) {
      const parsed = snapshotSchema.safeParse(rawSnapshot)
      expect(
        parsed.success,
        `Falha ao validar snapshot chave '${key}': ${JSON.stringify(parsed.error)}`,
      ).toBe(true)
    }
  })

  it('valida com sucesso o formato do histórico de runs conforme contrato /api/v1/runs', () => {
    const runsSummary = fixtures.runs.map((r) => ({
      id: r.id,
      collected_at: r.collected_at,
      period: r.period,
      estimated: r.estimated,
      total_cost: r.summary.total_cost,
      largest_service: r.summary.largest_service,
    }))

    const parsed = historySchema.safeParse({ runs: runsSummary })
    expect(
      parsed.success,
      `Falha ao validar histórico de runs: ${JSON.stringify(parsed.error)}`,
    ).toBe(true)
  })

  it('rejeita snapshot com data de coleta ingênua (sem fuso horário UTC ou offset)', () => {
    const base = fixtures.runs[0]
    expect(base).toBeDefined()
    if (!base) return
    const invalid = structuredClone(base)
    invalid.collected_at = '2026-10-20T12:00:00' // sem fuso
    const parsed = snapshotSchema.safeParse(invalid)
    expect(parsed.success).toBe(false)
  })

  it('rejeita snapshot onde start >= end no período', () => {
    const base = fixtures.runs[0]
    expect(base).toBeDefined()
    if (!base) return
    const invalid = structuredClone(base)
    invalid.period = { start: '2026-10-20', end: '2026-10-20' }
    const parsed = snapshotSchema.safeParse(invalid)
    expect(parsed.success).toBe(false)
  })

  it('rejeita formato de relatório desconhecido', () => {
    const base = fixtures.runs[0]
    expect(base).toBeDefined()
    if (!base) return
    const invalid = structuredClone(base)
    // @ts-expect-error teste de formato inválido
    invalid.report_formats = ['executavel_invalido']
    const parsed = snapshotSchema.safeParse(invalid)
    expect(parsed.success).toBe(false)
  })

  it('suporta alertas do tipo untagged e top_services com severidade info/warning', () => {
    const base = fixtures.runs[0]
    expect(base).toBeDefined()
    if (!base) return
    const valid = structuredClone(base)
    valid.alerts = [
      {
        id: 'alert-untagged',
        type: 'untagged',
        severity: 'warning',
        message: 'Recursos sem tag detectados',
      },
      {
        id: 'alert-top',
        type: 'top_services',
        severity: 'info',
        message: 'Top serviços computados',
      },
    ]
    const parsed = snapshotSchema.safeParse(valid)
    expect(parsed.success).toBe(true)
  })
})
