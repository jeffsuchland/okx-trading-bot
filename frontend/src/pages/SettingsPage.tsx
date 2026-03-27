import { useEffect, useState, useCallback } from 'react'
import InfoTooltip from '../components/InfoTooltip'

interface StrategyConfig {
  name: string
  config: Record<string, number>
}

interface ConfigData {
  strategy: StrategyConfig
  risk: Record<string, unknown>
}

const STRATEGIES = [
  {
    value: 'MeanReversionStrategy',
    label: 'Buy the Dip',
    icon: '📉',
    tagline: 'Buy when prices drop, sell when they bounce back',
    detail: 'This strategy watches for moments when a coin\'s price has dropped significantly below its average (oversold). It buys during these dips and sells when the price recovers. Think of it like buying on sale and selling at full price. It uses two well-known indicators (RSI and MACD) to time entries and exits.',
    bestFor: 'Volatile markets with clear up-and-down swings',
  },
  {
    value: 'GridTradingStrategy',
    label: 'Grid Trading',
    icon: '📊',
    tagline: 'Profit from price bouncing up and down in a range',
    detail: 'This strategy places a ladder of buy and sell orders at regular price intervals. When the price drops, it buys. When it rises, it sells. It doesn\'t try to predict direction — it profits from the natural back-and-forth movement. Works best when prices are moving sideways rather than trending strongly in one direction.',
    bestFor: 'Sideways or range-bound markets',
  },
]

const MEAN_REVERSION_PARAMS = [
  { key: 'rsi_period', label: 'Lookback Window', defaultVal: '14', infoTitle: 'RSI Period', info: 'How many recent price candles the bot examines to decide if the price is unusually high or low. A smaller number (e.g. 7) reacts faster but may give false signals. A larger number (e.g. 21) is smoother but slower to react. Default of 14 is the industry standard.' },
  { key: 'rsi_oversold', label: 'Buy Below', defaultVal: '30', infoTitle: 'RSI Oversold Threshold', info: 'When the "momentum score" drops below this number, the bot considers the price to be oversold (too cheap) and looks to buy. Lower values (e.g. 20) mean you only buy at extreme dips, which is safer but less frequent. Default of 30 is standard.' },
  { key: 'rsi_overbought', label: 'Sell Above', defaultVal: '70', infoTitle: 'RSI Overbought Threshold', info: 'When the "momentum score" rises above this number, the bot considers the price to be overbought (too expensive) and looks to sell. Higher values (e.g. 80) mean you hold longer, potentially capturing more profit but with more risk. Default of 70 is standard.' },
  { key: 'macd_fast', label: 'Fast Signal', defaultVal: '12', infoTitle: 'MACD Fast Period', info: 'The fast-moving average used to detect momentum changes. This tracks recent price action. Smaller = more responsive. Most traders use the default of 12.' },
  { key: 'macd_slow', label: 'Slow Signal', defaultVal: '26', infoTitle: 'MACD Slow Period', info: 'The slow-moving average that provides the baseline trend. When the fast signal crosses above this, it suggests upward momentum. Most traders use the default of 26.' },
  { key: 'macd_signal', label: 'Smoothing', defaultVal: '9', infoTitle: 'MACD Signal Line', info: 'Smooths out the difference between fast and slow signals to reduce noise. The standard value is 9. You generally don\'t need to change this.' },
]

const GRID_PARAMS = [
  { key: 'num_levels', label: 'Number of Orders', defaultVal: '10', infoTitle: 'Grid Levels', info: 'How many buy/sell order pairs to place in the grid. More levels = more trades but smaller profit per trade. Fewer levels = bigger moves needed but larger profit per trade. Start with 10 and adjust based on results.' },
  { key: 'spacing_pct', label: 'Price Gap Between Orders', defaultVal: '0.5', infoTitle: 'Grid Spacing %', info: 'The percentage price difference between each order level. For example, 0.5% means orders are placed every 0.5% apart. Tighter spacing = more frequent trades. Wider spacing = trades only on bigger price moves.' },
  { key: 'order_size_usdt', label: 'Amount Per Order', defaultVal: '10', infoTitle: 'Order Size (USDT)', info: 'How much USDT each grid order uses. This times the number of levels is your total capital commitment. Start small (e.g. $10) until you\'re comfortable with the strategy.' },
]

// API key names must match what PUT /api/config risk_manager.update_config() accepts.
// GET /api/config returns a nested risk status; we extract the editable params in loadConfig.
const RISK_FIELDS = [
  {
    key: 'spend_per_trade',
    label: 'How much per trade?',
    unit: 'USDT',
    defaultVal: '10',
    infoTitle: 'Trade Size',
    info: 'The amount of USDT the bot spends each time it opens a new position. Start small ($5-10) while learning. You can increase this as you gain confidence. This is NOT your total investment — it\'s the size of each individual trade.',
  },
  {
    key: 'max_total_exposure',
    label: 'Maximum money at risk',
    unit: 'USDT',
    defaultVal: '100',
    infoTitle: 'Maximum Exposure',
    info: 'The maximum total USDT the bot will have in open positions at any time. Once this limit is reached, the bot won\'t open new trades until existing ones close. Think of it as your "trading budget". Set this to an amount you\'re comfortable having in play.',
  },
  {
    key: 'stop_loss_pct',
    label: 'Auto-close losing trades at',
    unit: '%',
    defaultVal: '2',
    infoTitle: 'Stop Loss',
    info: 'If a trade loses this much, the bot automatically closes it to prevent bigger losses. For example, 2% means if you buy at $100 and it drops to $98, the bot sells. This is your safety net. Most beginners should use 2-3%.',
  },
  {
    key: 'max_drawdown_pct',
    label: 'Emergency stop if account drops',
    unit: '%',
    defaultVal: '5',
    infoTitle: 'Circuit Breaker',
    info: 'If your total account value drops by this percentage from its peak, ALL trading stops immediately. This is your emergency brake. For example, 5% means if your $10,000 account drops to $9,500, the bot halts. You\'ll need to manually restart.',
  },
  {
    key: 'max_daily_loss',
    label: 'Stop trading for the day after losing',
    unit: 'USDT',
    defaultVal: '50',
    infoTitle: 'Daily Loss Limit',
    info: 'The maximum amount the bot is allowed to lose in a single day. Once hit, it stops trading until the next day. This prevents bad days from becoming catastrophic. Set this to an amount where you\'d want to take a break and reassess.',
  },
]

export default function SettingsPage() {
  const [strategy, setStrategy] = useState<string>('MeanReversionStrategy')
  const [strategyParams, setStrategyParams] = useState<Record<string, string>>({})
  const [riskParams, setRiskParams] = useState<Record<string, string>>({})
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [saving, setSaving] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)

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
      // Extract editable risk params from the nested get_risk_status() shape:
      // Top-level: spend_per_trade, max_total_exposure, stop_loss_pct
      // Nested: circuit_breaker.max_drawdown_pct, daily_limit.max_daily_loss
      if (data.risk && typeof data.risk === 'object') {
        const risk = data.risk as Record<string, unknown>
        const rp: Record<string, string> = {}
        if (risk.spend_per_trade != null) rp.spend_per_trade = String(risk.spend_per_trade)
        if (risk.max_total_exposure != null) rp.max_total_exposure = String(risk.max_total_exposure)
        if (risk.stop_loss_pct != null) rp.stop_loss_pct = String(risk.stop_loss_pct)
        const cb = risk.circuit_breaker as Record<string, unknown> | undefined
        const dl = risk.daily_limit as Record<string, unknown> | undefined
        if (cb?.max_drawdown_pct != null) rp.max_drawdown_pct = String(cb.max_drawdown_pct)
        if (dl?.max_daily_loss != null) rp.max_daily_loss = String(dl.max_daily_loss)
        setRiskParams(rp)
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

      if (res.status === 422) {
        const err = await res.json()
        const detail = err?.detail
        let msg = 'Invalid values — check your inputs.'
        if (Array.isArray(detail) && detail.length > 0) {
          msg = detail.map((d: { msg?: string; loc?: string[] }) =>
            [d.loc?.slice(1).join('.'), d.msg].filter(Boolean).join(': ')
          ).join('; ')
        } else if (typeof detail === 'string') {
          msg = detail
        }
        setToast({ type: 'error', message: msg })
        return
      }

      if (!res.ok) throw new Error('Save failed')
      setToast({ type: 'success', message: 'Settings saved!' })
    } catch {
      setToast({ type: 'error', message: 'Failed to save. Is the backend running?' })
    } finally {
      setSaving(false)
    }
  }

  const currentStrategyParams =
    strategy === 'MeanReversionStrategy' ? MEAN_REVERSION_PARAMS : GRID_PARAMS

  return (
    <div data-testid="settings-page" className="max-w-3xl">
      <h1 className="text-2xl font-bold mb-1">Settings</h1>
      <p className="text-gray-400 text-sm mb-8">Set up how your bot trades and how much risk to take</p>

      {toast && (
        <div
          data-testid={`toast-${toast.type}`}
          className={`mb-6 p-4 rounded-xl text-sm flex items-center gap-3 ${
            toast.type === 'success'
              ? 'bg-green-900/30 text-green-400 border border-green-800/50'
              : 'bg-red-900/30 text-red-400 border border-red-800/50'
          }`}
        >
          <span className="text-lg">{toast.type === 'success' ? '✓' : '✕'}</span>
          {toast.message}
        </div>
      )}

      {/* ── Strategy Selection ── */}
      <section className="mb-8">
        <h2 className="text-base font-semibold mb-4">Choose Your Trading Strategy</h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {STRATEGIES.map((s) => (
            <button
              key={s.value}
              onClick={() => setStrategy(s.value)}
              className={`text-left rounded-xl p-5 border-2 transition-all ${
                strategy === s.value
                  ? 'border-blue-500 bg-blue-500/10 ring-1 ring-blue-500/30'
                  : 'border-gray-700 bg-gray-900 hover:border-gray-600'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">{s.icon}</span>
                <span className="font-semibold text-white">{s.label}</span>
                {strategy === s.value && (
                  <span className="ml-auto text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full">Active</span>
                )}
              </div>
              <p className="text-sm text-gray-400 mb-3">{s.tagline}</p>
              <p className="text-xs text-gray-500 leading-relaxed">{s.detail}</p>
              <p className="text-xs text-gray-600 mt-2">Best for: {s.bestFor}</p>
            </button>
          ))}
        </div>

        <input type="hidden" data-testid="strategy-dropdown" value={strategy} />
      </section>

      {/* ── Safety Settings ── */}
      <section className="mb-8">
        <h2 className="text-base font-semibold mb-1">Safety Limits</h2>
        <p className="text-gray-400 text-xs mb-4">These protect your money. The bot will automatically stop if any limit is hit.</p>

        <div data-testid="risk-params" className="space-y-3">
          {RISK_FIELDS.map(({ key, label, unit, defaultVal, infoTitle, info }) => (
            <div key={key} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-200">
                  {label}
                  <InfoTooltip title={infoTitle}>{info}</InfoTooltip>
                </span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  data-testid={`input-${key}`}
                  type="text"
                  inputMode="decimal"
                  placeholder={defaultVal}
                  value={riskParams[key] ?? ''}
                  onChange={(e) => handleRiskParamChange(key, e.target.value)}
                  className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white w-32 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono text-center"
                />
                <span className="text-sm text-gray-500">{unit}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Advanced Strategy Tuning (collapsed by default) ── */}
      <section className="mb-8">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors mb-3"
        >
          <span className={`transition-transform ${showAdvanced ? 'rotate-90' : ''}`}>&#9654;</span>
          Advanced: Fine-tune strategy parameters
        </button>

        {showAdvanced && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <p className="text-xs text-gray-500 mb-4">
              These control the technical details of your selected strategy. The defaults work well for most situations — only change these if you know what you're doing.
            </p>
            <div data-testid="strategy-params" className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {currentStrategyParams.map(({ key, label, defaultVal, infoTitle, info }) => (
                <div key={key} className="bg-gray-800/50 rounded-lg p-3 border border-gray-700/30">
                  <div className="flex items-center mb-2">
                    <label className="text-xs font-medium text-gray-300">{label}</label>
                    <InfoTooltip title={infoTitle}>{info}</InfoTooltip>
                  </div>
                  <input
                    data-testid={`input-${key}`}
                    type="text"
                    inputMode="decimal"
                    placeholder={defaultVal}
                    value={strategyParams[key] ?? ''}
                    onChange={(e) => handleStrategyParamChange(key, e.target.value)}
                    className="bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-white w-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none font-mono text-sm"
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ── Save ── */}
      <div className="flex items-center gap-4 pb-8">
        <button
          data-testid="save-button"
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-8 py-3 rounded-xl font-semibold transition-colors shadow-lg shadow-blue-600/20"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
        <button
          onClick={loadConfig}
          className="text-gray-400 hover:text-white px-4 py-3 rounded-xl text-sm transition-colors"
        >
          Reset
        </button>
      </div>
    </div>
  )
}
