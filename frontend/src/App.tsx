import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useEffect, useState, useCallback } from 'react'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import SettingsPage from './pages/SettingsPage'
import TradeLogPage from './pages/TradeLogPage'

function App() {
  const [status, setStatus] = useState<'running' | 'paused' | 'stopped'>('stopped')
  const [usdtBalance, setUsdtBalance] = useState(0)

  const fetchStatus = useCallback(async () => {
    try {
      const [statusRes, balanceRes] = await Promise.all([
        fetch('/api/status'),
        fetch('/api/balance'),
      ])
      if (statusRes.ok) {
        const data = await statusRes.json()
        setStatus(data.status as 'running' | 'paused' | 'stopped')
      }
      if (balanceRes.ok) {
        const data = await balanceRes.json()
        setUsdtBalance(data.usdt_available ?? 0)
      }
    } catch {
      // silent - dashboard page handles its own error state
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout status={status} usdtBalance={usdtBalance} onStatusChange={setStatus} />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/trade-log" element={<TradeLogPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
