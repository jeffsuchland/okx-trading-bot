import { useState } from 'react'

interface BotControlsProps {
  status: 'running' | 'paused' | 'stopped'
  onStatusChange?: (newStatus: string) => void
}

export default function BotControls({ status, onStatusChange }: BotControlsProps) {
  const [loading, setLoading] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message })
    setTimeout(() => setToast(null), 3000)
  }

  const handlePanicClick = () => {
    setShowConfirm(true)
  }

  const handlePanicConfirm = async () => {
    setShowConfirm(false)
    setLoading(true)
    try {
      const res = await fetch('/api/panic', { method: 'POST' })
      if (!res.ok) throw new Error('Panic failed')
      showToast('success', 'Panic mode activated')
      onStatusChange?.('stopped')
    } catch {
      showToast('error', 'Panic request failed')
    } finally {
      setLoading(false)
    }
  }

  const handleStartStop = async () => {
    setLoading(true)
    const endpoint = status === 'running' ? '/api/stop' : '/api/start'
    try {
      const res = await fetch(endpoint, { method: 'POST' })
      if (!res.ok) throw new Error('Action failed')
      const data = await res.json()
      onStatusChange?.(data.status)
      showToast('success', `Bot ${data.status}`)
    } catch {
      showToast('error', 'Action failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div data-testid="bot-controls" className="flex items-center gap-3">
      {toast && (
        <span
          data-testid={`controls-toast-${toast.type}`}
          className={`text-xs px-2 py-1 rounded ${
            toast.type === 'success' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
          }`}
        >
          {toast.message}
        </span>
      )}

      <button
        data-testid="start-stop-button"
        onClick={handleStartStop}
        disabled={loading}
        className={`px-4 py-1.5 rounded text-sm font-medium disabled:opacity-50 ${
          status === 'running'
            ? 'bg-gray-700 hover:bg-gray-600 text-white'
            : 'bg-green-600 hover:bg-green-700 text-white'
        }`}
      >
        {loading ? (
          <span data-testid="button-spinner" className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
        ) : status === 'running' ? (
          'Stop'
        ) : (
          'Start'
        )}
      </button>

      <button
        data-testid="panic-button"
        onClick={handlePanicClick}
        disabled={loading}
        className="bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white px-4 py-1.5 rounded text-sm font-bold uppercase tracking-wide"
      >
        Panic
      </button>

      {showConfirm && (
        <div data-testid="panic-modal" className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-lg p-6 max-w-sm mx-4">
            <h3 className="text-lg font-bold text-red-400 mb-2">Confirm Panic</h3>
            <p className="text-gray-300 text-sm mb-4">
              This will cancel all open orders and flatten all positions. Are you sure?
            </p>
            <div className="flex gap-3 justify-end">
              <button
                data-testid="panic-cancel"
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 text-sm text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                data-testid="panic-confirm"
                onClick={handlePanicConfirm}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm font-bold"
              >
                Confirm Panic
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
