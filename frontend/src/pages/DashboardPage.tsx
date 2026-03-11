import { useEffect, useState, useCallback } from 'react'

interface PnlData {
  daily_pnl: number
  cumulative_pnl: number
  win_rate: number
  recent_trades: Trade[]
}

interface BalanceData {
  usdt_available: number
  total_equity: number
  positions: unknown[]
}

interface Trade {
  timestamp: string
  symbol: string
  side: string
  qty: number
  price: number
  pnl: number
}

type FetchState = 'loading' | 'success' | 'error'

export default function DashboardPage() {
  const [pnl, setPnl] = useState<PnlData | null>(null)
  const [balance, setBalance] = useState<BalanceData | null>(null)
  const [state, setState] = useState<FetchState>('loading')

  const fetchData = useCallback(async () => {
    try {
      const [pnlRes, balRes] = await Promise.all([
        fetch('/api/pnl'),
        fetch('/api/balance'),
      ])
      if (!pnlRes.ok || !balRes.ok) throw new Error('API error')
      setPnl(await pnlRes.json())
      setBalance(await balRes.json())
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
      <div data-testid="dashboard-page">
        <div data-testid="loading-skeleton" className="animate-pulse space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-800 rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (state === 'error' && !pnl) {
    return (
      <div data-testid="dashboard-page">
        <div data-testid="error-state" className="text-red-400 p-4 bg-red-900/20 rounded-lg">
          Unable to connect to the bot API. Is the backend running?
        </div>
      </div>
    )
  }

  const dailyPnl = pnl?.daily_pnl ?? 0
  const cumulativePnl = pnl?.cumulative_pnl ?? 0
  const winRate = pnl?.win_rate ?? 0
  const equity = balance?.total_equity ?? 0
  const exposure = 0 // Will be populated from risk status later

  const cards = [
    {
      label: 'Daily PnL',
      value: dailyPnl,
      testId: 'card-daily-pnl',
      format: (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}`,
      colorClass: dailyPnl >= 0 ? 'text-green-400' : 'text-red-400',
    },
    {
      label: 'Cumulative PnL',
      value: cumulativePnl,
      testId: 'card-cumulative-pnl',
      format: (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}`,
      colorClass: cumulativePnl >= 0 ? 'text-green-400' : 'text-red-400',
    },
    {
      label: 'Win Rate',
      value: winRate,
      testId: 'card-win-rate',
      format: (v: number) => `${v.toFixed(1)}%`,
      colorClass: 'text-white',
    },
    {
      label: 'Current Exposure',
      value: exposure,
      testId: 'card-exposure',
      format: (v: number) => `$${v.toFixed(2)}`,
      colorClass: 'text-white',
    },
    {
      label: 'Account Equity',
      value: equity,
      testId: 'card-equity',
      format: (v: number) => `$${v.toFixed(2)}`,
      colorClass: 'text-white',
    },
  ]

  const trades = pnl?.recent_trades ?? []

  return (
    <div data-testid="dashboard-page">
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        {cards.map((card) => (
          <div
            key={card.testId}
            data-testid={card.testId}
            className="bg-gray-900 border border-gray-800 rounded-lg p-4"
          >
            <p className="text-xs text-gray-400 mb-1">{card.label}</p>
            <p className={`text-xl font-mono font-bold ${card.colorClass}`}>
              {card.format(card.value)}
            </p>
          </div>
        ))}
      </div>

      <h2 className="text-lg font-semibold mb-3">Recent Trades</h2>
      <div className="overflow-x-auto">
        <table data-testid="trades-table" className="w-full text-sm text-left">
          <thead className="text-gray-400 border-b border-gray-800">
            <tr>
              <th className="py-2 px-3">Timestamp</th>
              <th className="py-2 px-3">Symbol</th>
              <th className="py-2 px-3">Side</th>
              <th className="py-2 px-3">Qty</th>
              <th className="py-2 px-3">Price</th>
              <th className="py-2 px-3">PnL</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t, i) => (
              <tr key={i} className="border-b border-gray-800/50">
                <td className="py-2 px-3 text-gray-300">{t.timestamp}</td>
                <td className="py-2 px-3">{t.symbol}</td>
                <td className={`py-2 px-3 ${t.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                  {t.side}
                </td>
                <td className="py-2 px-3 font-mono">{t.qty}</td>
                <td className="py-2 px-3 font-mono">{t.price}</td>
                <td className={`py-2 px-3 font-mono ${t.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {t.pnl >= 0 ? '+' : ''}{t.pnl.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
