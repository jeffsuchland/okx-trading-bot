import { useEffect, useState, useCallback } from 'react'

interface StrategyConfig {
  name: string
  config: Record<string, number>
}

interface ConfigData {
  strategy: StrategyConfig
  risk: Record<string, unknown>
}

const STRATEGIES = [
  { value: 'MeanReversionStrategy', label: 'Mean Reversion (RSI + MACD)', description: 'Buys oversold dips, sells overbought rallies using RSI and MACD crossovers' },
  { value: 'GridTradingStrategy', label: 'Grid Trading', description: 'Places buy/sell orders at fixed price intervals to profit from sideways markets' },
]

const MEAN_REVERSION_PARAMS = [
  { key: 'rsi_period', label: 'RSI Period', description: 'Number of candles for RSI calculation', defaultVal: '14' },
  { key: 'rsi_oversold', label: 'RSI Oversold Level', description: 'Buy signal when RSI drops below this', defaultVal: '30' },
  { key: 'rsi_overbought', label: 'RSI Overbought Level', description: 'Sell signal when RSI rises above this', defaultVal: '70' },
  { key: 'macd_fast', label: 'MACD Fast Period', description: 'Fast EMA period for MACD', defaultVal: '12' },
  { key: 'macd_slow', label: 'MACD Slow Period', description: 'Slow EMA period for MACD', defaultVal: '26' },
  { key: 'macd_signal', label: 'MACD Signal Period', description: 'Signal line EMA period', defaultVal: '9' },
]

const GRID_PARAMS = [
  { key: 'num_levels', label: 'Grid Levels', description: 'Number of buy/sell price levels', defaultVal: '10' },
  { key: 'spacing_pct', label: 'Grid Spacing %', description: 'Price gap between each level', defaultVal: '0.5' },
  { key: 'order_size_usdt', label: 'Order Size (USDT)', description: 'Amount per grid order', defaultVal: '10' },
]

const RISK_FIELDS = [
  { key: 'spend_per_trade', label: 'Trade Size', description: 'USDT to spend per trade', unit: 'USDT' },
  { key: 'max_exposure', label: 'Max Exposure', description: 'Maximum total USDT in open positions', unit: 'USDT' },
  { key: 'stop_loss_pct', label: 'Stop Loss', description: 'Auto-close position if it drops by this %', unit: '%' },
  { key: 'max_drawdown_pct', label: 'Max Drawdown', description: 'Halt all trading if account drops by this %', unit: '%' },
  { key: 'daily_loss_limit', label: 'Daily Loss Limit', description: 'Stop trading for the day after losing this much', unit: 'USDT' },
]

export default function SettingsPage() {
  const [strategy, setStrategy] = useState<string>('MeanReversionStrategy')
  const [strategyParams, setStrategyParams] = useState<Record<string, string>>({})
  const [riskParams, setRiskParams] = useState<Record<string, string>>({})
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [saving, setSaving] = useState(false)

  const loadConfig = useCallback(async () => {
    try {
      const res = await fetch('/api/config')
      if (!res.ok) return
      const data: ConfigData = await res.json()
      if (data.strategy?.name) setStrategy(data.strategy.name)
      if (data.strategy?.config) {
        const params: Record<string, string> = {}
        for (const [k, v] of Object.entries(data.strategy.config)) {
          params[k] = String(v)
        }
        setStrategyParams(params)
      }
    } catch {
      // silent fail on load
    }
  }, [])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 3000)
      return () => clearTimeout(t)
    }
  }, [toast])

  const handleStrategyParamChange = (key: string, value: string) => {
    if (value !== '' && (isNaN(Number(value)) || Number(value) < 0)) return
    setStrategyParams((prev) => ({ ...prev, [key]: value }))
  }

  const handleRiskParamChange = (key: string, value: string) => {
    if (value !== '' && (isNaN(Number(value)) || Number(value) < 0)) return
    setRiskParams((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const stratConfig: Record<string, number> = {}
      for (const [k, v] of Object.entries(strategyParams)) {
        if (v !== '') stratConfig[k] = Number(v)
      }
      const riskConfig: Record<string, number> = {}
      for (const [k, v] of Object.entries(riskParams)) {
        if (v !== '') riskConfig[k] = Number(v)
      }

      const res = await fetch('/api/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy: stratConfig, risk: riskConfig }),
      })
      if (!res.ok) throw new Error('Save failed')
      setToast({ type: 'success', message: 'Settings saved successfully' })
    } catch {
      setToast({ type: 'error', message: 'Failed to save settings' })
    } finally {
      setSaving(false)
    }
  }

  const currentStrategyParams =
    strategy === 'MeanReversionStrategy' ? MEAN_REVERSION_PARAMS : GRID_PARAMS

  const selectedStrategy = STRATEGIES.find((s) => s.value === strategy)

  return (
    <div data-testid="settings-page" className="max-w-4xl">
      <h1 className="text-2xl font-bold mb-2">Settings</h1>
      <p className="text-gray-400 text-sm mb-6">Configure your trading strategy and risk parameters</p>

      {toast && (
        <div
          data-testid={`toast-${toast.type}`}
          className={`mb-6 p-4 rounded-lg text-sm flex items-center gap-2 ${
            toast.type === 'success'
              ? 'bg-green-900/30 text-green-400 border border-green-800/50'
              : 'bg-red-900/30 text-red-400 border border-red-800/50'
          }`}
        >
          <span>{toast.type === 'success' ? '✓' : '✕'}</span>
          {toast.message}
        </div>
      )}

      {/* Strategy Selection */}
      <section className="mb-8 bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-1">Trading Strategy</h2>
        <p className="text-gray-400 text-sm mb-4">Choose how the bot finds and executes trades</p>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-300 mb-2">Active Strategy</label>
          <select
            data-testid="strategy-dropdown"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white w-full max-w-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          >
            {STRATEGIES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
          {selectedStrategy && (
            <p className="text-gray-500 text-xs mt-2">{selectedStrategy.description}</p>
          )}
        </div>

        <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Strategy Parameters</h3>
        <div data-testid="strategy-params" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {currentStrategyParams.map(({ key, label, description, defaultVal }) => (
            <div key={key} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
              <label className="block text-sm font-medium text-gray-200 mb-1">{label}</label>
              <p className="text-xs text-gray-500 mb-2">{description}</p>
              <input
                data-testid={`input-${key}`}
                type="text"
                inputMode="decimal"
                placeholder={defaultVal}
                value={strategyParams[key] ?? ''}
                onChange={(e) => handleStrategyParamChange(key, e.target.value)}
                className="bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono"
              />
            </div>
          ))}
        </div>
      </section>

      {/* Risk Management */}
      <section className="mb-8 bg-gray-900 border border-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-1">Risk Management</h2>
        <p className="text-gray-400 text-sm mb-4">Set limits to protect your capital</p>

        <div data-testid="risk-params" className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {RISK_FIELDS.map(({ key, label, description, unit }) => (
            <div key={key} className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
              <label className="block text-sm font-medium text-gray-200 mb-1">{label}</label>
              <p className="text-xs text-gray-500 mb-2">{description}</p>
              <div className="relative">
                <input
                  data-testid={`input-${key}`}
                  type="text"
                  inputMode="decimal"
                  value={riskParams[key] ?? ''}
                  onChange={(e) => handleRiskParamChange(key, e.target.value)}
                  className="bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white w-full pr-14 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500">{unit}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Save Button */}
      <div className="flex items-center gap-4">
        <button
          data-testid="save-button"
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-8 py-3 rounded-lg font-semibold text-sm transition-colors shadow-lg shadow-blue-600/20"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
        <button
          onClick={loadConfig}
          className="text-gray-400 hover:text-white px-4 py-3 rounded-lg text-sm transition-colors"
        >
          Reset to Current
        </button>
      </div>
    </div>
  )
}
