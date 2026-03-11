import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Settings, ScrollText } from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/trade-log', label: 'Trade Log', icon: ScrollText },
]

interface SidebarProps {
  collapsed?: boolean
}

export default function Sidebar({ collapsed = false }: SidebarProps) {
  return (
    <aside
      data-testid="sidebar"
      className={`bg-gray-900 border-r border-gray-800 flex flex-col transition-all duration-200 ${
        collapsed ? 'w-16' : 'w-56'
      }`}
    >
      <div className="p-4 border-b border-gray-800">
        <h2 className={`font-bold text-lg text-white ${collapsed ? 'hidden' : ''}`}>
          OKX Bot
        </h2>
      </div>
      <nav className="flex-1 py-4">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 text-sm transition-colors ${
                isActive
                  ? 'bg-gray-800 text-white border-r-2 border-blue-500'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
              }`
            }
          >
            <Icon size={20} />
            {!collapsed && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
