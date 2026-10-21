import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  Activity,
  Bell,
  ChartNoAxesCombined,
  ChevronRight,
  Cloud,
  FlaskConical,
  History,
  LayoutDashboard,
  Menu,
  Moon,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Sun,
  X,
} from 'lucide-react'
import { useApp, useSnapshot } from './context'

const nav = [
  { path: '/', title: 'Visão geral', Icon: LayoutDashboard },
  { path: '/costs', title: 'Análise de custos', Icon: ChartNoAxesCombined },
  { path: '/alerts', title: 'Alertas FinOps', Icon: Bell },
  { path: '/ai', title: 'Analista IA', Icon: Sparkles },
  { path: '/history', title: 'Histórico', Icon: History },
]
function initialTheme(): 'dark' | 'light' {
  try {
    return localStorage.getItem('cost-monitor-theme') === 'light'
      ? 'light'
      : 'dark'
  } catch {
    return 'dark'
  }
}
export function Layout() {
  const { client, filters, setFilters } = useApp()
  const location = useLocation()
  const isSnapshot = ['/', '/costs', '/alerts', '/ai'].includes(
    location.pathname,
  )
  const query = useSnapshot(isSnapshot)
  const [theme, setTheme] = useState(initialTheme)
  const [menu, setMenu] = useState(false)
  const main = useRef<HTMLElement>(null)
  const menuButton = useRef<HTMLButtonElement>(null)
  const sidebar = useRef<HTMLElement>(null)
  useEffect(() => {
    if (!menu) return
    sidebar.current?.querySelector<HTMLAnchorElement>('nav a')?.focus()
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMenu(false)
        menuButton.current?.focus()
      }
    }
    document.addEventListener('keydown', close)
    return () => document.removeEventListener('keydown', close)
  }, [menu])
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      localStorage.setItem('cost-monitor-theme', theme)
    } catch {
      /* Theme still works without storage. */
    }
  }, [theme])
  useEffect(() => {
    const page =
      nav.find((item) => item.path === location.pathname)?.title ?? 'Histórico'
    document.title = `${page} · AWS Cost Monitor`
    main.current?.focus({ preventScroll: true })
    window.scrollTo(0, 0)
  }, [location.pathname])
  const current =
    nav.find((item) => item.path === location.pathname)?.title ?? 'Histórico'
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Pular para o conteúdo
      </a>
      <aside
        ref={sidebar}
        id="sidebar"
        className={`sidebar ${menu ? 'is-open' : ''}`}
        aria-label="Menu principal"
      >
        <NavLink className="brand" to="/" onClick={() => setMenu(false)}>
          <span className="brand-mark">
            <Cloud size={24} aria-hidden="true" />
          </span>
          <span>
            AWS Cost Monitor<small>FINOPS WORKSPACE</small>
          </span>
        </NavLink>
        <div className="workspace-label">
          <span className="workspace-icon">N</span>
          <div>
            Netto Labs<small>Ambiente de desenvolvimento</small>
          </div>
          <ChevronRight size={14} aria-hidden="true" />
        </div>
        <p className="nav-label">MONITORAMENTO</p>
        <nav aria-label="Navegação principal">
          {nav.map(({ path, title, Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              onClick={() => setMenu(false)}
            >
              <Icon size={19} aria-hidden="true" />
              {title}
              {path === '/ai' && (
                <span className="nav-new" aria-hidden="true">
                  IA
                </span>
              )}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="architecture-note">
            <ShieldCheck size={19} aria-hidden="true" />
            <strong>Clareza para decidir.</strong>
            <p>
              React apresenta.
              <br />
              Python calcula.
              <br />
              IA interpreta.
            </p>
          </div>
          <div className="sidebar-footer">
            <span className="avatar">NL</span>
            <div>
              Netto Labs<small>AWS Cost Monitor · v0.1</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              ref={menuButton}
              className="icon-button mobile-menu"
              aria-label={menu ? 'Fechar menu' : 'Abrir menu'}
              aria-expanded={menu}
              aria-controls="sidebar"
              onClick={() => setMenu(!menu)}
            >
              {menu ? <X size={21} /> : <Menu size={21} />}
            </button>
            <span>Workspace</span>
            <ChevronRight size={13} aria-hidden="true" />
            <strong>{current}</strong>
          </div>
          <div className="topbar-actions">
            <span className="connection-badge">
              <span />
              {client.mode === 'mock' ? 'Ambiente demo' : 'Modo API'}
            </span>
            <button
              className="icon-button"
              aria-label={`Ativar tema ${theme === 'dark' ? 'claro' : 'escuro'}`}
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            >
              {theme === 'dark' ? <Sun size={19} /> : <Moon size={19} />}
            </button>
          </div>
        </header>
        <main ref={main} id="main-content" tabIndex={-1}>
          <div
            className={`mode-banner ${client.mode === 'api' ? 'api-banner' : ''}`}
          >
            <FlaskConical size={17} aria-hidden="true" />
            <strong>
              {client.mode === 'mock' ? 'Dados simulados' : 'Integração API'}
            </strong>
            <span>
              {client.mode === 'mock'
                ? 'Explore o dashboard com um cenário ilustrativo. Nenhuma conexão com a AWS.'
                : 'Leitura de snapshots pela API configurada. Contrato FastAPI proposto; integração depende do backend.'}
            </span>
          </div>
          {isSnapshot && (
            <div className="global-filters">
              <div className="inline-filters">
                <label className="select-field">
                  <span>Período</span>
                  <select
                    value={filters.days}
                    onChange={(e) =>
                      setFilters({
                        ...filters,
                        days: Number(e.target.value) as 7 | 30 | 90,
                      })
                    }
                  >
                    {(query.data?.available_filters.days ?? [7, 30, 90]).map(
                      (days) => (
                        <option value={days} key={days}>
                          Últimos {days} dias
                        </option>
                      ),
                    )}
                  </select>
                </label>
                <label className="select-field">
                  <span>Tag</span>
                  <select
                    value={filters.tag}
                    onChange={(e) =>
                      setFilters({ ...filters, tag: e.target.value })
                    }
                  >
                    <option value="">Todas as tags</option>
                    {query.data?.available_filters.tags.map((tag) => (
                      <option key={tag}>{tag}</option>
                    ))}
                  </select>
                </label>
              </div>
              <button
                className="button subtle"
                disabled={query.isFetching}
                onClick={() => void query.refetch()}
              >
                <RefreshCw
                  size={15}
                  className={query.isFetching ? 'spin' : ''}
                  aria-hidden="true"
                />
                Atualizar snapshot
              </button>
            </div>
          )}
          <Outlet />
          <footer className="main-footer">
            <span>
              <Activity size={14} aria-hidden="true" />
              AWS Cost Monitor
            </span>
            <span>Visibilidade para sua nuvem. Controle para sua equipe.</span>
          </footer>
        </main>
      </div>
    </div>
  )
}
