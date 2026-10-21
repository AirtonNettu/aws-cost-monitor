import { createContext, useContext } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { DataClient, Filters } from '../api/contracts'

export const AppContext = createContext<{
  client: DataClient
  filters: Filters
  setFilters: (filters: Filters) => void
} | null>(null)
export function useApp() {
  const context = useContext(AppContext)
  if (!context) throw new Error('AppContext ausente')
  return context
}
export function useSnapshot(enabled = true) {
  const { client, filters } = useApp()
  return useQuery({
    enabled,
    queryKey: ['snapshot', client.mode, filters],
    queryFn: ({ signal }) => client.getSnapshot(filters, signal),
  })
}
