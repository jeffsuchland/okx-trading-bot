import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import BotControls from './BotControls'

describe('BotControls', () => {
  beforeEach(() => {
    vi.spyOn(global, 'fetch').mockImplementation((url) => {
      const u = typeof url === 'string' ? url : (url as Request).url
      if (u.includes('/api/panic')) {
        return Promise.resolve(new Response(JSON.stringify({ success: true })))
      }
      if (u.includes('/api/start')) {
        return Promise.resolve(new Response(JSON.stringify({ success: true, status: 'running' })))
      }
      if (u.includes('/api/stop')) {
        return Promise.resolve(new Response(JSON.stringify({ success: true, status: 'stopped' })))
      }
      return Promise.reject(new Error('Unknown'))
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders panic button prominently', () => {
    render(<BotControls status="running" />)
    const btn = screen.getByTestId('panic-button')
    expect(btn).toBeDefined()
    expect(btn.textContent).toBe('Panic')
    expect(btn.className).toContain('bg-red-600')
  })

  it('renders start/stop button', () => {
    render(<BotControls status="running" />)
    const btn = screen.getByTestId('start-stop-button')
    expect(btn).toBeDefined()
    expect(btn.textContent).toBe('Stop')
  })

  it('shows Start when stopped', () => {
    render(<BotControls status="stopped" />)
    expect(screen.getByTestId('start-stop-button').textContent).toBe('Start')
  })

  it('clicking panic shows confirmation modal', async () => {
    const user = userEvent.setup()
    render(<BotControls status="running" />)
    await user.click(screen.getByTestId('panic-button'))
    expect(screen.getByTestId('panic-modal')).toBeDefined()
    expect(screen.getByTestId('panic-confirm')).toBeDefined()
    expect(screen.getByTestId('panic-cancel')).toBeDefined()
  })

  it('cancel dismisses panic modal', async () => {
    const user = userEvent.setup()
    render(<BotControls status="running" />)
    await user.click(screen.getByTestId('panic-button'))
    await user.click(screen.getByTestId('panic-cancel'))
    expect(screen.queryByTestId('panic-modal')).toBeNull()
  })

  it('confirming panic calls POST /api/panic and shows success toast', async () => {
    const user = userEvent.setup()
    render(<BotControls status="running" />)
    await user.click(screen.getByTestId('panic-button'))
    await user.click(screen.getByTestId('panic-confirm'))

    await waitFor(() => {
      expect(screen.getByTestId('controls-toast-success')).toBeDefined()
      expect(screen.getByTestId('controls-toast-success').textContent).toContain('Panic')
    })
  })

  it('start button calls POST /api/start', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<BotControls status="stopped" onStatusChange={onChange} />)
    await user.click(screen.getByTestId('start-stop-button'))

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith('running')
    })
  })

  it('stop button calls POST /api/stop', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<BotControls status="running" onStatusChange={onChange} />)
    await user.click(screen.getByTestId('start-stop-button'))

    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith('stopped')
    })
  })

  it('buttons are disabled during API call', async () => {
    let resolvePromise: (v: Response) => void
    vi.spyOn(global, 'fetch').mockImplementation(
      () => new Promise((resolve) => { resolvePromise = resolve })
    )

    const user = userEvent.setup()
    render(<BotControls status="stopped" />)
    await user.click(screen.getByTestId('start-stop-button'))

    expect((screen.getByTestId('start-stop-button') as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByTestId('panic-button') as HTMLButtonElement).disabled).toBe(true)

    // Resolve the promise to clean up
    resolvePromise!(new Response(JSON.stringify({ success: true, status: 'running' })))
    await waitFor(() => {
      expect((screen.getByTestId('start-stop-button') as HTMLButtonElement).disabled).toBe(false)
    })
  })
})
