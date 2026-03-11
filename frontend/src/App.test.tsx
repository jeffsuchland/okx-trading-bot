import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import SettingsPage from './pages/SettingsPage'
import TradeLogPage from './pages/TradeLogPage'

function renderWithRouter(initialRoute = '/') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route element={<Layout status="running" usdtBalance={1234.56} />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/trade-log" element={<TradeLogPage />} />
        </Route>
      </Routes>
    </MemoryRouter>
  )
}

describe('App Layout', () => {
  it('renders sidebar with nav links', () => {
    renderWithRouter()
    expect(screen.getByTestId('sidebar')).toBeDefined()
    expect(screen.getByText('Dashboard')).toBeDefined()
    expect(screen.getByText('Settings')).toBeDefined()
    expect(screen.getByText('Trade Log')).toBeDefined()
  })

  it('renders status bar', () => {
    renderWithRouter()
    expect(screen.getByTestId('status-bar')).toBeDefined()
  })

  it('shows bot status dot', () => {
    renderWithRouter()
    const dot = screen.getByTestId('status-dot')
    expect(dot.className).toContain('bg-green-500')
  })

  it('shows USDT balance', () => {
    renderWithRouter()
    expect(screen.getByTestId('usdt-balance').textContent).toBe('1234.56')
  })

  it('shows status label', () => {
    renderWithRouter()
    expect(screen.getByTestId('status-label').textContent).toBe('Running')
  })

  it('renders main content area', () => {
    renderWithRouter()
    expect(screen.getByTestId('main-content')).toBeDefined()
  })

  it('has dark background', () => {
    renderWithRouter()
    const sidebar = screen.getByTestId('sidebar')
    expect(sidebar.className).toContain('bg-gray-900')
  })
})

describe('Routing', () => {
  it('renders Dashboard page at /', () => {
    renderWithRouter('/')
    expect(screen.getByTestId('dashboard-page')).toBeDefined()
  })

  it('renders Settings page at /settings', () => {
    renderWithRouter('/settings')
    expect(screen.getByTestId('settings-page')).toBeDefined()
  })

  it('renders Trade Log page at /trade-log', () => {
    renderWithRouter('/trade-log')
    expect(screen.getByTestId('tradelog-page')).toBeDefined()
  })
})
