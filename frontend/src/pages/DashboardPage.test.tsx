import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import DashboardPage from './DashboardPage'

const mockPnlData = {
  daily_pnl: 15.5,
  cumulative_pnl: 120.0,
  win_rate: 66.7,
  recent_trades: [
    { timestamp: '2026-03-10T12:00:00Z', symbol: 'BTC-USDT', side: 'buy', qty: 0.001, price: 42000, pnl: 5.0 },
    { timestamp: '2026-03-10T12:05:00Z', symbol: 'ETH-USDT', side: 'sell', qty: 0.1, price: 3000, pnl: -2.0 },
  ],
}

const mockBalanceData = {
  usdt_available: 1000.0,
  total_equity: 1500.0,
  positions: [],
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>
  )
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('shows loading skeleton initially', () => {
    vi.spyOn(global, 'fetch').mockImplementation(() => new Promise(() => {}))
    renderDashboard()
    expect(screen.getByTestId('loading-skeleton')).toBeDefined()
  })

  it('shows error state when API fails', async () => {
    vi.spyOn(global, 'fetch').mockRejectedValue(new Error('Network error'))
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('error-state')).toBeDefined()
    })
  })

  it('renders Daily PnL card with green styling for positive value', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : (url as Request).url
      if (u.includes('/api/pnl')) return Promise.resolve(new Response(JSON.stringify(mockPnlData)))
      if (u.includes('/api/balance')) return Promise.resolve(new Response(JSON.stringify(mockBalanceData)))
      return Promise.reject(new Error('Unknown URL'))
    })
    renderDashboard()
    await waitFor(() => {
      const card = screen.getByTestId('card-daily-pnl')
      expect(card).toBeDefined()
      expect(card.textContent).toContain('+$15.50')
      expect(card.querySelector('.text-green-400')).toBeTruthy()
    })
  })

  it('renders Cumulative PnL, Win Rate, Exposure, and Equity cards', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : (url as Request).url
      if (u.includes('/api/pnl')) return Promise.resolve(new Response(JSON.stringify(mockPnlData)))
      if (u.includes('/api/balance')) return Promise.resolve(new Response(JSON.stringify(mockBalanceData)))
      return Promise.reject(new Error('Unknown URL'))
    })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('card-cumulative-pnl')).toBeDefined()
      expect(screen.getByTestId('card-win-rate')).toBeDefined()
      expect(screen.getByTestId('card-exposure')).toBeDefined()
      expect(screen.getByTestId('card-equity')).toBeDefined()
    })
  })

  it('renders recent trades table with correct columns', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : (url as Request).url
      if (u.includes('/api/pnl')) return Promise.resolve(new Response(JSON.stringify(mockPnlData)))
      if (u.includes('/api/balance')) return Promise.resolve(new Response(JSON.stringify(mockBalanceData)))
      return Promise.reject(new Error('Unknown URL'))
    })
    renderDashboard()
    await waitFor(() => {
      const table = screen.getByTestId('trades-table')
      expect(table).toBeDefined()
      expect(table.textContent).toContain('Time')
      expect(table.textContent).toContain('Pair')
      expect(table.textContent).toContain('Side')
      expect(table.textContent).toContain('Quantity')
      expect(table.textContent).toContain('Price')
      expect(table.textContent).toContain('P&L')
      expect(table.textContent).toContain('BTC-USDT')
      expect(table.textContent).toContain('ETH-USDT')
    })
  })

  it('polls data every 5 seconds', async () => {
    const fetchSpy = vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : (url as Request).url
      if (u.includes('/api/pnl')) return Promise.resolve(new Response(JSON.stringify(mockPnlData)))
      if (u.includes('/api/balance')) return Promise.resolve(new Response(JSON.stringify(mockBalanceData)))
      return Promise.reject(new Error('Unknown URL'))
    })
    renderDashboard()
    await waitFor(() => {
      expect(screen.getByTestId('card-daily-pnl')).toBeDefined()
    })
    const initialCalls = fetchSpy.mock.calls.length

    await vi.advanceTimersByTimeAsync(5000)
    await waitFor(() => {
      expect(fetchSpy.mock.calls.length).toBeGreaterThan(initialCalls)
    })
  })

  it('shows red styling for negative Daily PnL', async () => {
    const negativePnl = { ...mockPnlData, daily_pnl: -10.0 }
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : (url as Request).url
      if (u.includes('/api/pnl')) return Promise.resolve(new Response(JSON.stringify(negativePnl)))
      if (u.includes('/api/balance')) return Promise.resolve(new Response(JSON.stringify(mockBalanceData)))
      return Promise.reject(new Error('Unknown URL'))
    })
    renderDashboard()
    await waitFor(() => {
      const card = screen.getByTestId('card-daily-pnl')
      expect(card.textContent).toContain('$10.00')
      expect(card.querySelector('.text-red-400')).toBeTruthy()
    })
  })
})
