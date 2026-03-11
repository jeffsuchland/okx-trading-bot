import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import DashboardPage from './pages/DashboardPage'
import SettingsPage from './pages/SettingsPage'
import TradeLogPage from './pages/TradeLogPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout status="stopped" usdtBalance={0} />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/trade-log" element={<TradeLogPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
