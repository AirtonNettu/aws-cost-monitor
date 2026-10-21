import { z } from 'zod'

const amount = z.number().finite()
const periodSchema = z.object({ start: z.iso.date(), end: z.iso.date() }).refine(p => p.start < p.end)
const reportFormatSchema = z.enum(['json', 'csv', 'html', 'markdown', 'txt'])
export const snapshotSchema = z.object({
  id: z.string().min(1),
  source: z.enum(['mock', 'aws']),
  collected_at: z.iso.datetime({ offset: true }),
  currency: z.literal('USD'),
  period: periodSchema,
  estimated: z.boolean(),
  tag: z.string().nullable(),
  summary: z.object({
    total_cost: amount,
    largest_service: z.string().nullable(),
    largest_service_percentage: amount.nullable(),
    alert_count: z.number().int().nonnegative(),
  }),
  comparison: z.object({
    previous_total: amount, current_total: amount, variation: amount.nullable(),
    equivalent_periods: z.boolean(), previous_period: periodSchema,
  }).nullable(),
  services: z.array(z.object({ name: z.string(), amount, percentage: amount })),
  timeline: z.array(z.object({ date: z.iso.date(), amount })),
  alerts: z.array(z.object({
    id: z.string(), type: z.enum(['growth', 'concentration', 'top_services', 'untagged']),
    severity: z.enum(['info', 'warning', 'critical']), message: z.string(),
  })),
  ai: z.object({
    status: z.enum(['ready', 'processing', 'unavailable']),
    text: z.string().nullable(), model: z.string().nullable(),
    observations: z.array(z.string()), recommendations: z.array(z.string()),
    potential_waste: z.array(z.string()), reason: z.string().nullable(),
  }),
  available_filters: z.object({ days: z.array(z.union([z.literal(7), z.literal(30), z.literal(90)])), tags: z.array(z.string()) }),
  report_formats: z.array(reportFormatSchema),
})
export const historySchema = z.object({ runs: z.array(snapshotSchema.pick({ id: true, collected_at: true, period: true, estimated: true }).extend({
  total_cost: amount, largest_service: z.string().nullable(),
})) })
export type Snapshot = z.infer<typeof snapshotSchema>
export type History = z.infer<typeof historySchema>
export type ReportFormat = z.infer<typeof reportFormatSchema>
export interface Filters { days: 7 | 30 | 90; tag: string }
export interface DataClient {
  mode: 'mock' | 'api'
  getSnapshot(filters: Filters, signal?: AbortSignal): Promise<Snapshot>
  getHistory(signal?: AbortSignal): Promise<History>
  getRun(id: string, signal?: AbortSignal): Promise<Snapshot>
  exportReport(id: string, format: ReportFormat, signal?: AbortSignal): Promise<Blob>
}
