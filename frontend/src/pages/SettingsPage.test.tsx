import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import SettingsPage from './SettingsPage'

const mockConfig = {
  strategy: {
    name: 'MeanReversionStrategy',
    config: { rsi_period: 14, rsi_oversold: 30, rsi_overbought: 70 },
  },
  risk: {},
}

function renderSettings() {
  return render(
    <MemoryRouter>
      <SettingsPage />
    </MemoryRouter>
  )
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.spyOn(global, 'fetch').mockImplementation((url, opts) => {
      const u = typeof url === 'string' ? url : (url as Request).url
      const method = opts?.method ?? 'GET'
      if (u.includes('/api/config') && method === 'GET') {
        return Promise.resolve(new Response(JSON.stringify(mockConfig)))
      }
      if (u.includes('/api/config') && method === 'PUT') {
        return Promise.resolve(new Response(JSON.stringify({ success: true })))
      }
      return Promise.reject(new Error('Unknown'))
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders strategy dropdown with registered strategies', async () => {
    renderSettings()
    await waitFor(() => {
      const dropdown = screen.getByTestId('strategy-dropdown')
      expect(dropdown).toBeDefined()
      expect(dropdown.querySelectorAll('option').length).toBe(2)
    })
  })

  it('pre-populates config values from GET /api/config', async () => {
    renderSettings()
    await waitFor(() => {
      const input = screen.getByTestId('input-rsi_period') as HTMLInputElement
      expect(input.value).toBe('14')
    })
  })

  it('renders strategy params dynamically based on selected strategy', async () => {
    renderSettings()
    await waitFor(() => {
      expect(screen.getByTestId('strategy-params')).toBeDefined()
      expect(screen.getByTestId('input-rsi_period')).toBeDefined()
    })

    // Switch to GridTradingStrategy
    const dropdown = screen.getByTestId('strategy-dropdown')
    fireEvent.change(dropdown, { target: { value: 'GridTradingStrategy' } })

    await waitFor(() => {
      expect(screen.getByTestId('input-num_levels')).toBeDefined()
      expect(screen.queryByTestId('input-rsi_period')).toBeNull()
    })
  })

  it('renders risk parameter inputs', async () => {
    renderSettings()
    await waitFor(() => {
      expect(screen.getByTestId('risk-params')).toBeDefined()
      expect(screen.getByTestId('input-spend_per_trade')).toBeDefined()
      expect(screen.getByTestId('input-max_exposure')).toBeDefined()
      expect(screen.getByTestId('input-stop_loss_pct')).toBeDefined()
      expect(screen.getByTestId('input-max_drawdown_pct')).toBeDefined()
      expect(screen.getByTestId('input-daily_loss_limit')).toBeDefined()
    })
  })

  it('prevents negative values in inputs', async () => {
    const user = userEvent.setup()
    renderSettings()
    await waitFor(() => {
      expect(screen.getByTestId('input-spend_per_trade')).toBeDefined()
    })
    const input = screen.getByTestId('input-spend_per_trade') as HTMLInputElement
    await user.type(input, '-5')
    // Negative sign should be rejected, input stays empty
    expect(input.value).toBe('5')
  })

  it('save button sends PUT /api/config and shows success toast', async () => {
    const user = userEvent.setup()
    renderSettings()
    await waitFor(() => {
      expect(screen.getByTestId('save-button')).toBeDefined()
    })

    await user.click(screen.getByTestId('save-button'))

    await waitFor(() => {
      expect(screen.getByTestId('toast-success')).toBeDefined()
      expect(screen.getByTestId('toast-success').textContent).toContain('saved')
    })
  })

  it('shows error toast when save fails', async () => {
    vi.spyOn(global, 'fetch').mockImplementation((url, opts) => {
      const u = typeof url === 'string' ? url : (url as Request).url
      const method = opts?.method ?? 'GET'
      if (u.includes('/api/config') && method === 'GET') {
        return Promise.resolve(new Response(JSON.stringify(mockConfig)))
      }
      if (u.includes('/api/config') && method === 'PUT') {
        return Promise.resolve(new Response('error', { status: 500 }))
      }
      return Promise.reject(new Error('Unknown'))
    })

    const user = userEvent.setup()
    renderSettings()
    await waitFor(() => {
      expect(screen.getByTestId('save-button')).toBeDefined()
    })

    await user.click(screen.getByTestId('save-button'))

    await waitFor(() => {
      expect(screen.getByTestId('toast-error')).toBeDefined()
      expect(screen.getByTestId('toast-error').textContent).toContain('Failed')
    })
  })
})
