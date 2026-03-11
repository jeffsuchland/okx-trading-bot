import BotControls from './BotControls'

interface StatusBarProps {
  status: 'running' | 'paused' | 'stopped'
  usdtBalance: number
  onStatusChange?: (status: 'running' | 'paused' | 'stopped') => void
}

const statusColors: Record<string, string> = {
  running: 'bg-green-500',
  paused: 'bg-yellow-500',
  stopped: 'bg-red-500',
}

const statusLabels: Record<string, string> = {
  running: 'Running',
  paused: 'Paused',
  stopped: 'Stopped',
}

export default function StatusBar({ status, usdtBalance, onStatusChange }: StatusBarProps) {
  return (
    <header
      data-testid="status-bar"
      className="h-14 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-6"
    >
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span
            data-testid="status-dot"
            className={`w-3 h-3 rounded-full ${statusColors[status] ?? 'bg-gray-500'} ${status === 'running' ? 'animate-pulse' : ''}`}
          />
          <span data-testid="status-label" className="text-sm font-medium text-gray-300">
            Bot {statusLabels[status] ?? 'Unknown'}
          </span>
        </div>
        <BotControls
          status={status}
          onStatusChange={(s) => onStatusChange?.(s as 'running' | 'paused' | 'stopped')}
        />
      </div>
      <div className="flex items-center gap-2 bg-gray-800/50 px-3 py-1.5 rounded-lg">
        <span className="text-xs text-gray-400">Balance</span>
        <span data-testid="usdt-balance" className="text-sm font-mono font-bold text-white">
          ${usdtBalance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </span>
        <span className="text-xs text-gray-500">USDT</span>
      </div>
    </header>
  )
}
