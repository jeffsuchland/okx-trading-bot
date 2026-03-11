import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import StatusBar from './StatusBar'

interface LayoutProps {
  status?: 'running' | 'paused' | 'stopped'
  usdtBalance?: number
  onStatusChange?: (status: 'running' | 'paused' | 'stopped') => void
}

export default function Layout({ status = 'stopped', usdtBalance = 0, onStatusChange }: LayoutProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <Sidebar collapsed={collapsed} />
      <div className="flex flex-col flex-1 min-w-0">
        <StatusBar status={status} usdtBalance={usdtBalance} onStatusChange={onStatusChange} />
        <main data-testid="main-content" className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
