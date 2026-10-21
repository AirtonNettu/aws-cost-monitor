import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Link, Route, Routes } from 'react-router-dom'
import type { DataClient, Filters } from '../api/contracts'
import { AppContext } from './context'
import { Layout } from './Layout'
import { SnapshotPage } from '../features/overview/SnapshotPage'
import { HistoryDetail, HistoryPage } from '../features/history/HistoryPage'
import { PageHeading } from '../components/States'

export function App({ client }: { client: DataClient }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            staleTime: 5 * 60 * 1000,
            refetchOnWindowFocus: false,
            refetchOnReconnect: false,
          },
        },
      }),
  )
  const [filters, setFilters] = useState<Filters>({ days: 30, tag: '' })
  return (
    <QueryClientProvider client={queryClient}>
      <AppContext.Provider value={{ client, filters, setFilters }}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<SnapshotPage kind="overview" />} />
            <Route path="costs" element={<SnapshotPage kind="costs" />} />
            <Route path="alerts" element={<SnapshotPage kind="alerts" />} />
            <Route path="ai" element={<SnapshotPage kind="ai" />} />
            <Route path="history" element={<HistoryPage />} />
            <Route path="history/:runId" element={<HistoryDetail />} />
            <Route
              path="*"
              element={
                <>
                  <PageHeading
                    title="Página não encontrada"
                    subtitle="Este endereço não faz parte do dashboard."
                  />
                  <Link to="/" className="button">
                    Voltar à visão geral
                  </Link>
                </>
              }
            />
          </Route>
        </Routes>
      </AppContext.Provider>
    </QueryClientProvider>
  )
}
