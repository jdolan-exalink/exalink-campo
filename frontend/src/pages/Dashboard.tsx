import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  RadioTower, Wifi, WifiOff, Battery, AlertTriangle, RefreshCw, Activity, Thermometer
} from 'lucide-react'
import api from '@/lib/api'
import { cn } from '@/lib/utils'
import type { MapData, MapAnimal, MapGateway, LoraDevice, LoraGateway, Paddock, Establishment } from '@/types'
import KPICard from '@/components/dashboard/KPICard'
import WeatherWidget from '@/components/dashboard/WeatherWidget'
import AlertsFeed from '@/components/dashboard/AlertsFeed'
import LiveMap from '@/components/map/LiveMap'
import Header from '@/components/layout/Header'

const toMapAnimal = (d: LoraDevice, defLat?: number, defLon?: number): MapAnimal | null => {
  const lat = d.lat != null ? Number(d.lat) : (defLat ?? null)
  const lon = d.lon != null ? Number(d.lon) : (defLon ?? null)
  if (lat == null || lon == null) return null
  return {
    device_id: d.dev_addr,
    device_uid: d.name || d.dev_addr,
    animal_id: null, name: d.name, field_id: null, field_name: null,
    paddock_id: null, paddock_name: null, outside_field: false,
    gateway_id: d.gateway_id,
    lat, lon, battery_pct: d.battery_pct, temperature: d.temperature,
    is_online: d.online > 0, online: d.online,
    last_seen: d.last_seen, device_type: d.device_type || 'sensor',
    gps_fresh: d.gps_fresh,
  }
}

export default function Dashboard() {
  const { data: devices = [], refetch } = useQuery<LoraDevice[]>({
    queryKey: ['dashboard-devices'],
    queryFn: () => api.get('/lora/devices').then(r => r.data.devices),
    refetchInterval: 15_000,
  })

  const { data: gws = [] } = useQuery<LoraGateway[]>({
    queryKey: ['dashboard-gateways'],
    queryFn: () => api.get('/lora/gateways').then(r => r.data.gateways),
    refetchInterval: 30_000,
  })

  const { data: fields = [] } = useQuery<Establishment[]>({
    queryKey: ['dashboard-fields'],
    queryFn: () => api.get('/establishments').then(r => r.data),
    refetchInterval: 30_000,
  })

  const { data: paddocks = [] } = useQuery<Paddock[]>({
    queryKey: ['dashboard-paddocks'],
    queryFn: () => api.get('/paddocks').then(r => r.data),
    refetchInterval: 30_000,
  })

  const alertsQuery = useQuery<any[]>({
    queryKey: ['alerts-feed'],
    queryFn: () => api.get('/alerts?status=open&limit=20').then(r => r.data),
    refetchInterval: 15_000,
  })

  const devicesList = devices
  const gwsList = gws

  const mapData = useMemo<MapData>(() => {
    const defLat = fields[0]?.lat ?? undefined
    const defLon = fields[0]?.lon ?? undefined
    const animals = devicesList
      .map(d => toMapAnimal(d, defLat, defLon))
      .filter((item): item is MapAnimal => item !== null)
    const gateways: MapGateway[] = gwsList
      .map(g => ({
        gateway_id: g.gateway_id,
        name: g.name,
        lat: g.lat != null ? Number(g.lat) : (fields[0]?.lat ?? -31.6317),
        lon: g.lon != null ? Number(g.lon) : (fields[0]?.lon ?? -60.6877),
        online: g.online,
        battery_pct: g.battery_pct,
        last_seen: g.last_seen,
        device_count: g.device_count,
      }))
    const features = [
      ...fields
        .filter(f => f.boundary != null)
        .map(f => ({
          type: 'Feature' as const,
          properties: { id: f.id, name: f.name, kind: 'field' as const, status: 'Campo', current_load: 0, max_capacity: null, color: f.color || '#3b82f6' },
          geometry: f.boundary!,
        })),
      ...paddocks
        .filter(p => p.polygon != null)
        .map(p => ({
          type: 'Feature' as const,
          properties: { id: p.id, name: p.name, kind: 'paddock' as const, status: p.status, current_load: p.current_load, max_capacity: p.max_capacity, color: p.color || '#22c55e' },
          geometry: p.polygon!,
        })),
    ]
    return {
      animals,
      gateways,
      paddocks: { type: 'FeatureCollection' as const, features },
      alerts: alertsQuery.data ?? [],
    }
  }, [devicesList, gwsList, fields, paddocks, alertsQuery.data])

  const online = devicesList.filter(d => d.online >= 1).length
  const offline = devicesList.filter(d => d.online === 0).length
  const lowBat = devicesList.filter(d => d.battery_pct != null && d.battery_pct <= 10).length
  const weakSignal = devicesList.filter(d => d.online === 2).length
  const gwOnline = gwsList.filter(g => g.online > 0).length
  const avgTemp = devicesList.filter(d => d.temperature != null).length > 0
    ? devicesList.reduce((s, d) => s + (d.temperature ?? 0), 0) / devicesList.filter(d => d.temperature != null).length
    : null

  return (
    <div className="flex flex-col h-full">
      <Header title="Dashboard" subtitle="Monitoreo en tiempo real" />

      <div className="flex-1 overflow-auto p-3 sm:p-4 lg:p-6 space-y-3 sm:space-y-4 lg:space-y-6">
        {/* KPI Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2 sm:gap-3 lg:gap-4">
          <KPICard title="Online" value={online} icon={Wifi} color="green" />
          <KPICard title="Offline" value={offline} icon={WifiOff} color="red" alert={offline > 0} />
          <KPICard title="Señal débil" value={weakSignal} icon={Activity} color="yellow" alert={weakSignal > 0} />
          <KPICard title="Bat. baja" value={lowBat} icon={Battery} color="yellow" alert={lowBat > 0} />
          <KPICard title="Gateways" value={`${gwOnline}/${gws.length}`} icon={RadioTower} color="blue" />
          <KPICard
            title="Temp prom"
            value={avgTemp != null ? `${avgTemp.toFixed(1)}°C` : '—'}
            icon={Thermometer}
            color={avgTemp != null && avgTemp > 35 ? 'red' : avgTemp != null && avgTemp < 5 ? 'blue' : 'slate'}
          />
        </div>

        {/* Refresh button */}
        <div className="flex justify-end">
          <button onClick={() => refetch()} className="btn-secondary text-xs">
            <RefreshCw size={14} /> Actualizar
          </button>
        </div>

        {/* Weather widget */}
        {fields[0]?.lat != null && fields[0]?.lon != null && (
          <WeatherWidget lat={fields[0].lat} lon={fields[0].lon} fieldName={fields[0]?.name} />
        )}

        {/* Map + Alerts */}
        <div className="flex flex-col lg:flex-row gap-3 sm:gap-4" style={{ minHeight: '360px' }}>
          <div className="flex-1 card overflow-hidden min-h-[260px] sm:min-h-[300px]">
            <LiveMap data={mapData} />
          </div>
          <div className="w-full lg:w-80 flex-shrink-0 max-h-[360px] lg:max-h-none">
            <AlertsFeed />
          </div>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 lg:gap-4">
          <div className="card p-3 sm:p-4 lg:p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Dispositivos</h3>
            <div className="space-y-2 text-sm">
              {devices.map(d => (
                <div key={d.dev_addr} className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${d.online >= 1 ? 'bg-emerald-400' : d.online === 2 ? 'bg-amber-400' : 'bg-slate-500'}`} />
                    <span className="text-slate-300 truncate text-xs">{d.name || d.dev_addr}</span>
                  </div>
                  <span className="text-xs text-slate-400 tabular-nums flex-shrink-0">
                    {d.battery_pct != null ? `${Math.round(d.battery_pct)}%` : '—'}
                  </span>
                </div>
              ))}
              {devices.length === 0 && <p className="text-xs text-slate-500">Sin dispositivos</p>}
            </div>
          </div>

          <div className="card p-3 sm:p-4 lg:p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Gateways</h3>
            <div className="space-y-2 text-sm">
              {gws.map(g => {
                const tOut = g.temperature != null && (g.temperature > 38 || g.temperature < 5)
                const bLow = g.battery_pct != null && g.battery_pct <= 20
                return (
                  <div key={g.gateway_id} className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className={`w-2 h-2 rounded-full flex-shrink-0 ${g.online > 0 ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                      <span className="text-slate-300 truncate text-xs">{g.name || g.gateway_id}</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs tabular-nums flex-shrink-0">
                      {g.temperature != null && (
                        <span className={cn(tOut ? 'text-danger' : 'text-slate-400')} title="Temperatura">
                          {g.temperature.toFixed(1)}°C
                        </span>
                      )}
                      {g.humidity != null && (
                        <span className="text-slate-400" title="Humedad">{g.humidity.toFixed(0)}%</span>
                      )}
                      {g.battery_pct != null && (
                        <span className={cn(bLow ? 'text-danger' : 'text-slate-400')} title="Bateria">
                          {g.battery_pct.toFixed(0)}%
                        </span>
                      )}
                      <span className={cn(g.online > 0 ? 'text-emerald-400' : 'text-slate-500')}>
                        {g.online > 0 ? 'Online' : 'Offline'}
                      </span>
                    </div>
                  </div>
                )
              })}
              {gws.length === 0 && <p className="text-xs text-slate-500">Sin gateways</p>}
            </div>
          </div>

          <div className="card p-3 sm:p-4 lg:p-5 sm:col-span-2 lg:col-span-1">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">Alertas activas</h3>
            {(mapData as any).alerts?.length > 0 ? (
              <div className="space-y-2">
                {(mapData as any).alerts.slice(0, 5).map((a: any) => (
                  <div key={a.id} className="flex items-center gap-2 text-xs">
                    <AlertTriangle size={12} className={a.severity === 'critical' ? 'text-danger flex-shrink-0' : 'text-warning flex-shrink-0'} />
                    <span className="text-slate-300 truncate">{a.title}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500">Sin alertas</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
