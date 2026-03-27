import { useEffect, useState, useCallback } from 'react'

interface Trade {
  timestamp: string
  symbol: string
  side: string
  qty: number
  price: number
  pnl: number
}

interface PnlData {
  daily_pnl: number
  cumulative_pnl: number
  win_rate: number
  recent_trades: Trade[]
}

type FetchState = 'loading' | 'success' | 'error'

function formatUsd(v: number): string {
  return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function TradeLogPage() {
  const [pnl, setPnl] = useState<PnlData | null>(null)
  const [state, setState] = useState<FetchState>('loading')

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch('/api/pnl')
      if (!res.ok) throw new Error('API error')
      setPnl(await res.json())
      setState('success')
    } catch {
      setState('error')
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [fetchData])

  if (state === 'loading' && !pnl) {
    return (
      <div data-testid="tradelog-page">
        <div data-testid="loading-skeleton" className="animate-pulse space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-24 bg-gray-800 rounded-xl" />
            ))}
          </div>
          <div className="h-64 bg-gray-800 rounded-xl" />
        </div>
      </div>
    )
  }

  if (state === 'error' && !pnl) {
    return (
      <div data-testid="tradelog-page">
        <div data-testid="error-state" className="text-red-400 p-6 bg-red-900/20 rounded-xl border border-red-800/30 text-center">
          <p className="text-lg font-semibold mb-1">Unable to connect to the bot API</p>
          <p className="text-sm text-red-400/70">Make sure the backend is running with: python main.py</p>
        </div>
      </div>
    )
  }

  const trades = pnl?.recent_trades ?? []
  const winRate = pnl?.win_rate ?? 0
  const totalPnl = pnl?.cumulative_pnl ?? 0
  const totalTrades = trades.length

  const summaryStats = [
    {
      label: 'Total Trades',
      value: String(totalTrades),
      colorClass: 'text-white',
      testId: 'stat-total-trades',
    },
    {
      label: 'Win Rate',
      value: `${winRate.toFixed(1)}%`,
      colorClass: winRate >= 50 ? 'text-green-400' : winRate > 0 ? 'text-yellow-400' : 'text-gray-400',
      testId: 'stat-win-rate',
    },
    {
      label: 'Total P&L',
      value: `${totalPnl >= 0 ? '+' : ''}$${formatUsd(Math.abs(totalPnl))}`,
      colorClass: totalPnl >= 0 ? 'text-green-400' : 'text-red-400',
      testId: 'stat-total-pnl',
    },
  ]

  return (
    <div data-testid="tradelog-page">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Trade Log</h1>
          <p className="text-gray-400 text-sm">Full history of executed trades</p>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {summaryStats.map((stat) => (
          <div
            key={stat.testId}
            data-testid={stat.testId}
            className="bg-gray-900 border border-gray-800 rounded-xl p-5"
          >
            <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
              {stat.label}
            </p>
            <p className={`text-2xl font-mono font-bold ${stat.colorClass}`}>
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      {/* Trade History Table */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Trade History</h2>
          <span className="text-xs text-gray-500">{totalTrades} trades</span>
        </div>

        {trades.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500 text-sm">No trades yet</p>
            <p className="text-gray-600 text-xs mt-1">Trades will appear here once the bot starts executing</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table data-testid="trades-table" className="w-full text-sm text-left">
              <thead className="text-xs text-gray-400 border-b border-gray-800 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-3">Time</th>
                  <th className="py-3 px-3">Pair</th>
                  <th className="py-3 px-3">Side</th>
                  <th className="py-3 px-3 text-right">Quantity</th>
                  <th className="py-3 px-3 text-right">Price</th>
                  <th className="py-3 px-3 text-right">P&L</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t, i) => (
                  <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                    <td className="py-3 px-3 text-gray-400 text-xs">{t.timestamp}</td>
                    <td className="py-3 px-3 font-medium">{t.symbol}</td>
                    <td className="py-3 px-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                        t.side === 'buy'
                          ? 'bg-green-900/30 text-green-400'
                          : 'bg-red-900/30 text-red-400'
                      }`}>
                        {t.side.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-right">{t.qty}</td>
                    <td className="py-3 px-3 font-mono text-right">${formatUsd(t.price)}</td>
                    <td className={`py-3 px-3 font-mono text-right font-semibold ${
                      t.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {t.pnl >= 0 ? '+' : ''}${formatUsd(Math.abs(t.pnl))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
