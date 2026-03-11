import { useEffect, useState, useCallback } from 'react'

interface StrategyConfig {
  name: string
  config: Record<string, number>
}

interface ConfigData {
  strategy: StrategyConfig
  risk: Record<string, unknown>
}

const STRATEGIES = ['MeanReversionStrategy', 'GridTradingStrategy']

const RISK_FIELDS = [
  { key: 'spend_per_trade', label: 'Spend Per Trade (USDT)', min: 0 },
  { key: 'max_exposure', label: 'Max Exposure (USDT)', min: 0 },
  { key: 'stop_loss_pct', label: 'Stop Loss %', min: 0 },
  { key: 'max_drawdown_pct', label: 'Max Drawdown %', min: 0 },
  { key: 'daily_loss_limit', label: 'Daily Loss Limit (USDT)', min: 0 },
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

  const strategyInputs =
    strategy === 'MeanReversionStrategy'
      ? ['rsi_period', 'rsi_oversold', 'rsi_overbought', 'macd_fast', 'macd_slow', 'macd_signal']
      : ['num_levels', 'spacing_pct', 'order_size_usdt']

  return (
    <div data-testid="settings-page">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      {toast && (
        <div
          data-testid={`toast-${toast.type}`}
          className={`mb-4 p-3 rounded-lg text-sm ${
            toast.type === 'success' ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
          }`}
        >
          {toast.message}
        </div>
      )}

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-4">Strategy</h2>
        <div className="mb-4">
          <label className="block text-sm text-gray-400 mb-1">Active Strategy</label>
          <select
            data-testid="strategy-dropdown"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white w-64"
          >
            {STRATEGIES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        <div data-testid="strategy-params" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {strategyInputs.map((key) => (
            <div key={key}>
              <label className="block text-sm text-gray-400 mb-1">{key}</label>
              <input
                data-testid={`input-${key}`}
                type="text"
                inputMode="decimal"
                value={strategyParams[key] ?? ''}
                onChange={(e) => handleStrategyParamChange(key, e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white w-full"
              />
            </div>
          ))}
        </div>
      </section>

      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-4">Risk Management</h2>
        <div data-testid="risk-params" className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {RISK_FIELDS.map(({ key, label }) => (
            <div key={key}>
              <label className="block text-sm text-gray-400 mb-1">{label}</label>
              <input
                data-testid={`input-${key}`}
                type="text"
                inputMode="decimal"
                value={riskParams[key] ?? ''}
                onChange={(e) => handleRiskParamChange(key, e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white w-full"
              />
            </div>
          ))}
        </div>
      </section>

      <button
        data-testid="save-button"
        onClick={handleSave}
        disabled={saving}
        className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-6 py-2 rounded font-medium"
      >
        {saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  )
}
