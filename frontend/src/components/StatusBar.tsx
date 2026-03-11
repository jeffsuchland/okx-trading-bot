interface StatusBarProps {
  status: 'running' | 'paused' | 'stopped'
  usdtBalance: number
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

export default function StatusBar({ status, usdtBalance }: StatusBarProps) {
  return (
    <header
      data-testid="status-bar"
      className="h-14 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-6"
    >
      <div className="flex items-center gap-3">
        <span
          data-testid="status-dot"
          className={`w-3 h-3 rounded-full ${statusColors[status] ?? 'bg-gray-500'}`}
        />
        <span data-testid="status-label" className="text-sm text-gray-300">
          {statusLabels[status] ?? 'Unknown'}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-400">USDT</span>
        <span data-testid="usdt-balance" className="text-sm font-mono text-white">
          {usdtBalance.toFixed(2)}
        </span>
      </div>
    </header>
  )
}
