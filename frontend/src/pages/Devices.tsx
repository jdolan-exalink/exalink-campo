import { useQuery } from '@tanstack/react-query'
import { Cpu, Wifi, WifiOff, Battery, BatteryLow, Signal } from 'lucide-react'
import api from '@/lib/api'
import type { Device } from '@/types'
import { deviceTypeLabel, timeAgo, cn } from '@/lib/utils'
import Header from '@/components/layout/Header'

function BatteryBar({ pct }: { pct: number | null }) {
  if (pct === null) return <span className="text-slate-500 text-xs">—</span>
  const color = pct <= 20 ? 'bg-danger' : pct <= 40 ? 'bg-warning' : 'bg-field'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-surface-700 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className={cn('text-xs tabular-nums', pct <= 20 ? 'text-danger' : pct <= 40 ? 'text-warning' : 'text-slate-400')}>
        {pct}%
      </span>
    </div>
  )
}

export default function Devices() {
  const { data: devices = [], isLoading } = useQuery<Device[]>({
    queryKey: ['devices'],
    queryFn: () => api.get('/devices').then(r => r.data),
    refetchInterval: 30_000,
  })

  const online = devices.filter(d => d.is_online).length
  const offline = devices.filter(d => !d.is_online).length
  const lowBattery = devices.filter(d => d.battery_pct !== null && d.battery_pct <= 20).length

  return (
    <div className="flex flex-col h-full">
      <Header title="Dispositivos" subtitle={`${devices.length} registrados · ${online} online · ${offline} offline`} />

      <div className="flex-1 overflow-auto p-6">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-field/20 flex items-center justify-center">
              <Wifi size={16} className="text-field" />
            </div>
            <div>
              <p className="text-xl font-bold text-white tabular-nums">{online}</p>
              <p className="text-xs text-slate-400">Online</p>
            </div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-danger/20 flex items-center justify-center">
              <WifiOff size={16} className="text-danger" />
            </div>
            <div>
              <p className="text-xl font-bold text-white tabular-nums">{offline}</p>
              <p className="text-xs text-slate-400">Offline</p>
            </div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-warning/20 flex items-center justify-center">
              <BatteryLow size={16} className="text-warning" />
            </div>
            <div>
              <p className="text-xl font-bold text-white tabular-nums">{lowBattery}</p>
              <p className="text-xs text-slate-400">Batería baja</p>
            </div>
          </div>
        </div>

        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-700">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Estado</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">UID</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Tipo</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Animal</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Batería</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">RSSI</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Temperatura</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Firmware</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Última señal</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Ubicación</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i} className="border-b border-surface-700">
                      {Array.from({ length: 10 }).map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-surface-700 rounded animate-pulse" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : (
                  devices.map((device) => (
                    <tr key={device.id} className="table-row">
                      <td className="px-4 py-3">
                        {device.is_online ? (
                          <span className="flex items-center gap-1.5 text-field text-xs">
                            <span className="w-1.5 h-1.5 rounded-full bg-field animate-pulse" />
                            Online
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5 text-slate-500 text-xs">
                            <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                            Offline
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 font-mono text-white text-xs">{device.device_uid}</td>
                      <td className="px-4 py-3 text-slate-400 text-xs">{deviceTypeLabel[device.device_type]}</td>
                      <td className="px-4 py-3 text-slate-300 font-mono text-xs">{device.animal_ear_tag || '—'}</td>
                      <td className="px-4 py-3"><BatteryBar pct={device.battery_pct} /></td>
                      <td className="px-4 py-3 text-slate-400 text-xs tabular-nums">
                        {device.rssi != null ? `${device.rssi} dBm` : '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs tabular-nums">
                        {device.temperature != null ? `${device.temperature.toFixed(1)}°C` : '—'}
                      </td>
                      <td className="px-4 py-3 text-slate-500 text-xs font-mono">{device.firmware || '—'}</td>
                      <td className="px-4 py-3 text-slate-400 text-xs">{timeAgo(device.last_seen)}</td>
                      <td className="px-4 py-3 text-slate-500 text-xs font-mono">
                        {device.last_lat != null ? `${device.last_lat.toFixed(4)}, ${device.last_lon?.toFixed(4)}` : '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
