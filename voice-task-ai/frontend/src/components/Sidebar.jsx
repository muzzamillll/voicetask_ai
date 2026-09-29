import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Mic,
  CheckSquare,
  ShoppingCart,
  Wallet,
  Users,
  BarChart3,
} from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/voice-notes', label: 'Voice Notes', icon: Mic },
  { to: '/tasks', label: 'Tasks', icon: CheckSquare },
  { to: '/orders', label: 'Orders', icon: ShoppingCart },
  { to: '/payments', label: 'Payments', icon: Wallet },
  { to: '/contacts', label: 'Contacts', icon: Users },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
]

function Sidebar() {
  return (
    <aside className="w-60 shrink-0 bg-white border-r border-gray-200 h-screen sticky top-0 flex flex-col">
      <div className="px-6 py-5 border-b border-gray-100">
        <h1 className="text-lg font-bold text-gray-800">VoiceTask AI</h1>
        <p className="text-xs text-gray-400 mt-0.5">Pakistani voice → tasks</p>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-indigo-50 text-indigo-700'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              }`
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}

export default Sidebar
