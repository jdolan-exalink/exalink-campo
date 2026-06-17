import { useNavigate } from 'react-router-dom'
import { Bell, Wifi, WifiOff, RadioTower, Menu } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { DashboardKPIs, LoraDevice, LoraGateway } from '@/types'
import { useSidebar } from './MainLayout'

interface HeaderProps {
  title: string
  subtitle?: string
  actions?: React.ReactNode
}

export default function Header({ title, subtitle, actions }: HeaderProps) {
  const navigate = useNavigate()
  const { toggleSidebar } = useSidebar()

  const { data: kpis } = useQuery<DashboardKPIs>({
    queryKey: ['kpis'],
    queryFn: () => api.get('/dashboard/kpis').then(r => r.data),
    refetchInterval: 30_000,
  })

  const { data: devData } = useQuery<{ devices: LoraDevice[] }>({
    queryKey: ['header-devices'],
    queryFn: () => api.get('/lora/devices').then(r => r.data),
    refetchInterval: 20_000,
  })

  const { data: gwData } = useQuery<{ gateways: LoraGateway[] }>({
    queryKey: ['header-gateways'],
    queryFn: () => api.get('/lora/gateways').then(r => r.data),
    refetchInterval: 20_000,
  })

  const devices = devData?.devices ?? []
  const online = devices.filter(d => d.online >= 1).length
  const offline = devices.filter(d => d.online === 0).length
  const gws = gwData?.gateways ?? []
  const gwOnline = gws.filter(g => g.online > 0).length
  const gwTotal = gws.length
  const openAlerts = kpis?.open_alerts ?? 0
  const hasOffline = offline > 0
  const hasGwOffline = gwOnline < gwTotal

  return (
    <header className="bg-surface-900 border-b border-surface-800 px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-2">
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <button
          onClick={toggleSidebar}
          className="lg:hidden p-1.5 text-slate-400 hover:text-slate-200 hover:bg-surface-800 rounded-lg transition-colors flex-shrink-0"
        >
          <Menu size={20} />
        </button>
        <div className="min-w-0">
          <h1 className="text-base sm:text-lg font-semibold text-white truncate">{title}</h1>
          {subtitle && <p className="text-xs sm:text-sm text-slate-400 hidden sm:block">{subtitle}</p>}
        </div>
      </div>
      <div className="flex items-center gap-2 sm:gap-4 flex-shrink-0">
        {actions}
        <div className="hidden sm:flex items-center gap-3 text-sm">
          <span className="flex items-center gap-1.5 text-emerald-400">
            <Wifi size={14} />
            {online} online
          </span>
          {hasOffline && (
            <span className="flex items-center gap-1.5 text-danger">
              <WifiOff size={14} />
              {offline} offline
            </span>
          )}
          <span className={`flex items-center gap-1.5 ${hasGwOffline ? 'text-danger' : 'text-emerald-400'}`}>
            <RadioTower size={14} />
            {gwOnline}/{gwTotal} GW
          </span>
        </div>
        <button onClick={() => navigate('/alerts')} className="relative p-2 text-slate-400 hover:text-slate-200 hover:bg-surface-800 rounded-lg transition-colors">
          <Bell size={18} />
          <span className={`absolute top-1 right-1 w-2.5 h-2.5 rounded-full ${hasOffline ? 'bg-danger animate-pulse' : 'bg-emerald-400'}`} />
          {openAlerts > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full bg-danger text-white text-[10px] flex items-center justify-center font-bold">
              {openAlerts > 9 ? '9+' : openAlerts}
            </span>
          )}
        </button>
      </div>
    </header>
  )
}
