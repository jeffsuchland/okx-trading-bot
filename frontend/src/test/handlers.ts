import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/status', () => {
    return HttpResponse.json({
      status: 'running',
      uptime: 3600,
      active_strategy: 'MeanReversionStrategy',
      heartbeat_ts: Date.now(),
    })
  }),

  http.get('/api/balance', () => {
    return HttpResponse.json({
      usdt_available: 1000.0,
      total_equity: 1500.0,
      positions: [],
    })
  }),

  http.get('/api/pnl', () => {
    return HttpResponse.json({
      daily_pnl: 25.5,
      cumulative_pnl: 150.0,
      win_rate: 0.65,
      recent_trades: [
        {
          id: 't1',
          symbol: 'BTC-USDT',
          side: 'buy',
          qty: '0.001',
          price: '42000.00',
          pnl: 12.5,
          ts: Date.now() - 60000,
        },
      ],
    })
  }),

  http.get('/api/config', () => {
    return HttpResponse.json({
      strategy: {
        name: 'MeanReversionStrategy',
        config: { rsi_period: 14, rsi_oversold: 30, rsi_overbought: 70 },
      },
      risk: {
        spend_per_trade: 10,
        max_exposure: 100,
        stop_loss_pct: 2,
        max_drawdown_pct: 10,
        daily_loss_limit: 50,
      },
    })
  }),

  http.put('/api/config', () => {
    return HttpResponse.json({ success: true })
  }),

  http.post('/api/panic', () => {
    return HttpResponse.json({ success: true, message: 'Panic mode activated' })
  }),

  http.post('/api/start', () => {
    return HttpResponse.json({ success: true, status: 'running' })
  }),

  http.post('/api/stop', () => {
    return HttpResponse.json({ success: true, status: 'stopped' })
  }),
]
