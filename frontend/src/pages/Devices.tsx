import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import {
  Cpu, Wifi, WifiOff, Battery, BatteryLow, BatteryFull, RadioTower, Satellite,
  MapPin, X, Thermometer, Droplet, Activity, LineChart as ChartIcon
} from 'lucide-react'
import api from '@/lib/api'
import type { LoraDevice, LoraGateway } from '@/types'
import { formatDateTime, cn } from '@/lib/utils'
import Header from '@/components/layout/Header'

export default function Devices() {
  const { data: devicesData } = useQuery<{ devices: LoraDevice[] }>({
    queryKey: ['lora-devices-all'],
    queryFn: () => api.get('/lora/devices').then(r => r.data),
    refetchInterval: 15_000,
  })
  const { data: gwsData } = useQuery<{ gateways: LoraGateway[] }>({
    queryKey: ['lora-gateways-all'],
    queryFn: () => api.get('/lora/gateways').then(r => r.data),
    refetchInterval: 30_000,
  })

  const [historyAddr, setHistoryAddr] = useState<string | null>(null)

  const devices = devicesData?.devices ?? []
  const gateways = gwsData?.gateways ?? []

  const allOnline = [
    ...gateways.filter(g => g.online > 0),
    ...devices.filter(d => d.online >= 1),
  ].length
  const allOffline = gateways.length + devices.length - allOnline
  const lowBattery = [
    ...gateways.filter(g => g.battery_pct != null && g.battery_pct <= 20),
    ...devices.filter(d => d.battery_pct != null && d.battery_pct <= 20),
  ].length

  const statusDot = (online: number) => {
    if (online >= 1) return <span className="w-2 h-2 rounded-full bg-field animate-pulse block" title="Conectado" />
    return <span className="w-2 h-2 rounded-full bg-slate-600 block" title="Desconectado" />
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Dispositivos"
        subtitle={`${gateways.length + devices.length} totales · ${allOnline} online · ${allOffline} offline`}
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-field/20 flex items-center justify-center"><Wifi size={16} className="text-field" /></div>
            <div><p className="text-xl font-bold text-white tabular-nums">{allOnline}</p><p className="text-xs text-slate-400">Online</p></div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-slate-600/20 flex items-center justify-center"><WifiOff size={16} className="text-slate-400" /></div>
            <div><p className="text-xl font-bold text-white tabular-nums">{allOffline}</p><p className="text-xs text-slate-400">Offline</p></div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-purple-500/20 flex items-center justify-center"><RadioTower size={16} className="text-purple-400" /></div>
            <div><p className="text-xl font-bold text-white tabular-nums">{gateways.length}</p><p className="text-xs text-slate-400">Gateways</p></div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-warning/20 flex items-center justify-center"><BatteryLow size={16} className="text-warning" /></div>
            <div><p className="text-xl font-bold text-white tabular-nums">{lowBattery}</p><p className="text-xs text-slate-400">Bateria baja</p></div>
          </div>
        </div>

        {/* Tabla unificada */}
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-700">
                  <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase w-6"></th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Tipo</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">ID / Nombre</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Bateria</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Temp</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Hum</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">GPS</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Paq.</th>
                  <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Ultima</th>
                  <th className="px-2 py-2 uppercase w-16"></th>
                </tr>
              </thead>
              <tbody>
                {/* Gateways */}
                {gateways.map(gw => (
                  <tr key={'gw-' + gw.gateway_id} className="table-row border-b border-surface-700/50">
                    <td className="px-2 py-2">{statusDot(gw.online)}</td>
                    <td className="px-2 py-2"><span className="flex items-center gap-1 text-xs text-purple-400"><RadioTower size={12} />GW</span></td>
                    <td className="px-2 py-2">
                      <p className="font-mono text-xs text-white">{gw.gateway_id}</p>
                      <p className="text-[10px] text-slate-500">{gw.name || 'Sin nombre'}</p>
                    </td>
                    <td className="px-2 py-2">{gw.battery_pct != null ? <span className={cn('flex items-center gap-1 text-xs tabular-nums', gw.battery_pct <= 20 ? 'text-danger' : gw.battery_pct <= 50 ? 'text-warning' : 'text-field')}>{gw.battery_pct <= 20 ? <BatteryLow size={13} /> : <Battery size={13} />}{gw.battery_pct.toFixed(0)}%</span> : '—'}</td>
                    <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{gw.temperature != null ? `${gw.temperature.toFixed(1)}°C` : '—'}</td>
                    <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{gw.humidity != null ? `${gw.humidity.toFixed(0)}%` : '—'}</td>
                    <td className="px-2 py-2 text-slate-500 text-xs">{gw.lat != null ? `${gw.lat.toFixed(4)},${gw.lon?.toFixed(4)}` : '—'}</td>
                    <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{gw.total_packets ?? 0}</td>
                    <td className="px-2 py-2 text-slate-400 text-xs whitespace-nowrap">{gw.last_seen ? formatDateTime(gw.last_seen) : '—'}</td>
                    <td className="px-2 py-2"></td>
                  </tr>
                ))}

                {/* Clientes LoRa */}
                {devices.map(dev => (
                  <tr key={'dev-' + dev.dev_addr} className="table-row">
                    <td className="px-2 py-2">{statusDot(dev.online)}</td>
                    <td className="px-2 py-2"><span className="flex items-center gap-1 text-xs text-cyan-400"><Satellite size={12} />Cliente</span></td>
                    <td className="px-2 py-2">
                      <p className="font-mono text-xs text-white">{dev.dev_addr}</p>
                      <p className="text-[10px] text-slate-500">{dev.name || 'Sin nombre'}</p>
                    </td>
                    <td className="px-2 py-2">{dev.battery_pct != null ? <span className={cn('flex items-center gap-1 text-xs tabular-nums', dev.battery_pct <= 20 ? 'text-danger' : dev.battery_pct <= 50 ? 'text-warning' : 'text-field')}>{dev.battery_pct <= 20 ? <BatteryLow size={13} /> : dev.battery_pct >= 80 ? <BatteryFull size={13} /> : <Battery size={13} />}{dev.battery_pct.toFixed(0)}%</span> : '—'}</td>
                    <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{dev.temperature != null ? `${dev.temperature.toFixed(1)}°C` : '—'}</td>
                    <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{dev.humidity != null ? `${dev.humidity.toFixed(0)}%` : '—'}</td>
                    <td className="px-2 py-2">
                      {dev.lat != null && dev.lon != null ? (
                        <span className="flex items-center gap-1 text-xs font-mono">
                          <MapPin size={11} className={dev.gps_fresh === 1 ? 'text-field' : 'text-slate-500'} />
                          <span className={dev.gps_fresh === 1 ? 'text-field' : 'text-slate-500'}>{dev.lat.toFixed(4)},{dev.lon.toFixed(4)}</span>
                        </span>
                      ) : <span className="text-slate-500 text-xs">—</span>}
                    </td>
                    <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{dev.total_packets ?? 0}</td>
                    <td className="px-2 py-2 text-slate-400 text-xs whitespace-nowrap">{(dev.updated_at || dev.last_seen) ? formatDateTime(dev.updated_at || dev.last_seen) : '—'}</td>
                    <td className="px-2 py-2">
                      <button onClick={() => setHistoryAddr(dev.dev_addr)} className="text-slate-400 hover:text-purple-400 p-1"><ChartIcon size={14} /></button>
                    </td>
                  </tr>
                ))}

                {gateways.length === 0 && devices.length === 0 && (
                  <tr><td colSpan={10} className="px-3 py-12 text-center text-slate-500">No hay dispositivos registrados</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {historyAddr && <DeviceHistoryModal devAddr={historyAddr} onClose={() => setHistoryAddr(null)} />}
    </div>
  )
}


function DeviceHistoryModal({ devAddr, onClose }: { devAddr: string; onClose: () => void }) {
  const { data, isLoading } = useQuery<{ points: Record<string, any>[] }>({
    queryKey: ['device-sensor-history', devAddr],
    queryFn: () => api.get(`/lora/devices/${devAddr}/sensor-history`, { params: { limit: 100 } }).then(r => r.data),
  })

  const points = data?.points ?? []
  const hasTemp = points.some(p => p.t != null)
  const hasHum  = points.some(p => p.h != null)
  const hasBat  = points.some(p => p.b != null)
  const hasGps  = points.some(p => p.lt != null)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-surface-900 border border-surface-700 rounded-xl p-6 w-full max-w-3xl max-h-[85vh] overflow-auto shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <ChartIcon size={18} className="text-purple-400" />
            Historial — <span className="font-mono text-sm">{devAddr}</span>
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1"><X size={18} /></button>
        </div>

        {isLoading ? (
          <div className="h-64 flex items-center justify-center text-slate-500">Cargando...</div>
        ) : points.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-slate-500">Sin datos historicos</div>
        ) : (
          <div className="space-y-4">
            {hasTemp && (
              <div className="card p-3">
                <p className="text-xs text-slate-400 mb-2 flex items-center gap-1"><Thermometer size={12} /> Temperatura (°C)</p>
                <ResponsiveContainer width="100%" height={140}>
                  <LineChart data={points}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="ts" tick={{ fontSize: 9, fill: '#6b7280' }} tickFormatter={(v: string) => v?.substring(11, 16)} />
                    <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={['auto', 'auto']} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
                    <Line type="monotone" dataKey="t" stroke="#f59e0b" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
            {hasHum && (
              <div className="card p-3">
                <p className="text-xs text-slate-400 mb-2 flex items-center gap-1"><Droplet size={12} /> Humedad (%)</p>
                <ResponsiveContainer width="100%" height={140}>
                  <LineChart data={points}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="ts" tick={{ fontSize: 9, fill: '#6b7280' }} tickFormatter={(v: string) => v?.substring(11, 16)} />
                    <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
                    <Line type="monotone" dataKey="h" stroke="#06b6d4" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
            {hasBat && (
              <div className="card p-3">
                <p className="text-xs text-slate-400 mb-2 flex items-center gap-1"><Activity size={12} /> Bateria (%)</p>
                <ResponsiveContainer width="100%" height={140}>
                  <LineChart data={points}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="ts" tick={{ fontSize: 9, fill: '#6b7280' }} tickFormatter={(v: string) => v?.substring(11, 16)} />
                    <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
                    <Line type="monotone" dataKey="b" stroke="#22c55e" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
            {hasGps && (
              <div className="card p-3">
                <p className="text-xs text-slate-400 mb-2 flex items-center gap-1"><MapPin size={12} /> GPS (ultimos 5)</p>
                <div className="space-y-1">
                  {points.filter(p => p.lt != null).slice(-5).reverse().map((p, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs text-slate-300 font-mono">
                      <MapPin size={11} className="text-field" />
                      {p.lt?.toFixed(5)}, {p.ln?.toFixed(5)}
                      <span className="text-slate-500">{p.ts?.substring(11, 16)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <p className="text-[10px] text-slate-500 text-center">{points.length} muestras</p>
          </div>
        )}
      </div>
    </div>
  )
}
