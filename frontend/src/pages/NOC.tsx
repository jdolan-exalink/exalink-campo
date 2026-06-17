import { useQuery } from '@tanstack/react-query'
import { Monitor, Users, Cpu, AlertCircle } from 'lucide-react'
import api from '@/lib/api'
import { cn } from '@/lib/utils'
import Header from '@/components/layout/Header'

interface TenantOverview {
  tenant_id: string
  tenant_name: string
  tenant_slug: string
  plan: string
  animals: number
  devices_online: number
  devices_total: number
  critical_alerts: number
}

export default function NOC() {
  const { data, isLoading } = useQuery<{ tenants: TenantOverview[]; total_tenants: number }>({
    queryKey: ['noc-overview'],
    queryFn: () => api.get('/noc/overview').then(r => r.data),
    refetchInterval: 30_000,
  })

  const { data: devices = [], isLoading: devLoading } = useQuery<any[]>({
    queryKey: ['noc-devices'],
    queryFn: () => api.get('/noc/devices').then(r => r.data),
    refetchInterval: 30_000,
  })

  return (
    <div className="flex flex-col h-full">
      <Header title="NOC — Centro de Operaciones" subtitle="Vista global de todos los tenants" />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Tenant overview */}
        <div>
          <h2 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <Users size={15} className="text-brand-400" />
            Tenants ({data?.total_tenants ?? 0})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {isLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-32 bg-surface-800 rounded-xl animate-pulse" />
              ))
            ) : (
              data?.tenants.map((t) => (
                <div key={t.tenant_id} className={cn(
                  'card p-4',
                  t.critical_alerts > 0 && 'border-danger/30'
                )}>
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="font-medium text-white">{t.tenant_name}</p>
                      <p className="text-xs text-slate-500 font-mono">{t.tenant_slug} · {t.plan}</p>
                    </div>
                    {t.critical_alerts > 0 && (
                      <span className="badge text-xs text-danger bg-danger/10 border-danger/20">
                        <AlertCircle size={10} /> {t.critical_alerts}
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div className="bg-surface-900 rounded-lg p-2">
                      <p className="text-lg font-bold text-white tabular-nums">{t.animals}</p>
                      <p className="text-[10px] text-slate-500">Animales</p>
                    </div>
                    <div className="bg-surface-900 rounded-lg p-2">
                      <p className={cn('text-lg font-bold tabular-nums', t.devices_online > 0 ? 'text-field' : 'text-slate-500')}>
                        {t.devices_online}
                      </p>
                      <p className="text-[10px] text-slate-500">Online</p>
                    </div>
                    <div className="bg-surface-900 rounded-lg p-2">
                      <p className="text-lg font-bold text-white tabular-nums">{t.devices_total}</p>
                      <p className="text-[10px] text-slate-500">Dispositivos</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Device table */}
        <div>
          <h2 className="text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
            <Cpu size={15} className="text-brand-400" />
            Dispositivos ({devices.length})
          </h2>
          <div className="card overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-surface-700">
                  <th className="px-4 py-2 text-left text-slate-400">Estado</th>
                  <th className="px-4 py-2 text-left text-slate-400">UID</th>
                  <th className="px-4 py-2 text-left text-slate-400">Tipo</th>
                  <th className="px-4 py-2 text-left text-slate-400">Tenant</th>
                  <th className="px-4 py-2 text-left text-slate-400">Batería</th>
                  <th className="px-4 py-2 text-left text-slate-400">Firmware</th>
                  <th className="px-4 py-2 text-left text-slate-400">Última señal</th>
                </tr>
              </thead>
              <tbody>
                {devLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-surface-700">
                      {Array.from({ length: 7 }).map((_, j) => (
                        <td key={j} className="px-4 py-2"><div className="h-3 bg-surface-700 rounded animate-pulse" /></td>
                      ))}
                    </tr>
                  ))
                ) : devices.slice(0, 50).map((d: any) => (
                  <tr key={d.device_uid} className="table-row">
                    <td className="px-4 py-2">
                      <span className={cn('w-1.5 h-1.5 rounded-full inline-block mr-1.5', d.is_online ? 'bg-field' : 'bg-slate-500')} />
                      {d.is_online ? 'Online' : 'Offline'}
                    </td>
                    <td className="px-4 py-2 font-mono text-slate-300">{d.device_uid}</td>
                    <td className="px-4 py-2 text-slate-400">{d.device_type}</td>
                    <td className="px-4 py-2 text-slate-400 font-mono">{d.tenant_id?.slice(0, 8)}...</td>
                    <td className="px-4 py-2">
                      {d.battery_pct != null ? (
                        <span className={cn(d.battery_pct <= 20 ? 'text-danger' : d.battery_pct <= 40 ? 'text-warning' : 'text-slate-400')}>
                          {d.battery_pct}%
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-2 font-mono text-slate-500">{d.firmware || '—'}</td>
                    <td className="px-4 py-2 text-slate-400">
                      {d.last_seen ? new Date(d.last_seen).toLocaleString('es-AR') : 'Nunca'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
