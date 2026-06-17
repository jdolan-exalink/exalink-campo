import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, Beef, Layers, Cpu, Bell, Syringe,
  Heart, Scale, Map, Monitor, RadioTower, LogOut, ChevronRight, X
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/animals', icon: Beef, label: 'Animales' },
  { to: '/paddocks', icon: Layers, label: 'Potreros' },
  { to: '/devices', icon: Cpu, label: 'Dispositivos' },
  { to: '/alerts', icon: Bell, label: 'Alertas' },
  { to: '/health', icon: Syringe, label: 'Sanidad' },
  { to: '/reproduction', icon: Heart, label: 'Reproducción' },
  { to: '/weights', icon: Scale, label: 'Pesajes' },
  { to: '/map', icon: Map, label: 'Mapa' },
  { to: '/lora', icon: RadioTower, label: 'LoRaWAN' },
]

const adminItems = [
  { to: '/noc', icon: Monitor, label: 'NOC' },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export default function Sidebar({ open, onClose }: SidebarProps) {
  const { user, logout } = useAuthStore()

  const sidebarContent = (
    <>
      {/* Logo + close button */}
      <div className="px-5 py-5 border-b border-surface-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold text-sm">
            EC
          </div>
          <div>
            <p className="text-white font-semibold text-sm leading-tight">Exalink</p>
            <p className="text-brand-400 text-xs font-medium">Campo</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="lg:hidden p-1.5 text-slate-400 hover:text-slate-200 hover:bg-surface-800 rounded-lg transition-colors"
        >
          <X size={18} />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <div className="px-3 space-y-0.5">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all group',
                  isActive
                    ? 'bg-brand-600/20 text-brand-400 font-medium'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-surface-800'
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={16} className={isActive ? 'text-brand-400' : 'text-slate-500 group-hover:text-slate-300'} />
                  <span className="flex-1">{label}</span>
                  {isActive && <ChevronRight size={12} className="text-brand-400" />}
                </>
              )}
            </NavLink>
          ))}
        </div>

        {user?.role === 'superadmin' && (
          <>
            <div className="px-5 py-3 mt-2">
              <p className="text-xs text-slate-600 uppercase tracking-wider font-medium">Administración</p>
            </div>
            <div className="px-3 space-y-0.5">
              {adminItems.map(({ to, icon: Icon, label }) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={onClose}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all',
                      isActive
                        ? 'bg-brand-600/20 text-brand-400 font-medium'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-surface-800'
                    )
                  }
                >
                  <Icon size={16} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </div>
          </>
        )}
      </nav>

      {/* User */}
      <div className="border-t border-surface-800 p-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-brand-700 flex items-center justify-center text-white text-xs font-bold">
            {user?.full_name.charAt(0).toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-slate-200 truncate font-medium">{user?.full_name}</p>
            <p className="text-xs text-slate-500 truncate">{user?.role}</p>
          </div>
          <button onClick={logout} className="text-slate-500 hover:text-danger transition-colors p-1 rounded">
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </>
  )

  return (
    <>
      {/* Desktop: static sidebar */}
      <aside className="hidden lg:flex w-60 flex-shrink-0 bg-surface-950 border-r border-surface-800 flex-col h-screen sticky top-0">
        {sidebarContent}
      </aside>

      {/* Mobile: overlay drawer */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-60 bg-surface-950 border-r border-surface-800 flex flex-col',
          'transition-transform duration-300 ease-in-out lg:hidden',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {sidebarContent}
      </aside>
    </>
  )
}
