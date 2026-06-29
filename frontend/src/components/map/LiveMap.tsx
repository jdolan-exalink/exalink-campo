import { useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, Marker, Tooltip, Popup, GeoJSON, LayersControl, useMap } from 'react-leaflet'
import { Maximize2, Minimize2 } from 'lucide-react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import api from '@/lib/api'
import type { MapAnimal, MapData, MapGateway, TemperatureHistoryResponse, BatteryHistoryResponse, ConsumptionResponse } from '@/types'

const batteryColor = (battery: number | null) => {
  if (battery == null) return '#94a3b8'
  if (battery <= 20) return '#ef4444'
  if (battery <= 50) return '#f59e0b'
  return '#22c55e'
}

const typeStyle = (type: string, online: number) => {
  if (online === 0) return { color: '#64748b', glyph: offlineSvg() }
  if (online === 2) return { color: '#f59e0b', glyph: weakSvg() }
  switch (type) {
    case 'gateway':
      return { color: '#3b82f6', glyph: gatewaySvg() }
    case 'gps_collar':
    case 'gps_tag':
    case 'animal':
      return { color: '#22c55e', glyph: animalSvg() }
    default:
      return { color: '#a855f7', glyph: sensorSvg() }
  }
}

const weakSvg = () => `
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
    <circle cx="12" cy="12" r="7" fill="currentColor"/>
    <path d="M8 8l8 8" stroke="#0f172a" stroke-width="2" stroke-linecap="round"/>
    <circle cx="12" cy="12" r="1.5" fill="#f59e0b"/>
  </svg>`

const animalSvg = () => `
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
    <path fill="currentColor" d="M4.5 10.5C5 8 6.5 8 7.5 9.5L8.5 8l8 0 1-1.5c1-1.5 2.5-1.5 3 1v5c0 2.5-2 4-4.5 4h-8c-2.5 0-4.5-1.5-4.5-4v-5Z"/>
    <circle cx="9" cy="12" r="1.2" fill="#0f172a"/>
    <circle cx="15" cy="12" r="1.2" fill="#0f172a"/>
  </svg>`

const gatewaySvg = () => `
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
    <path d="M12 20V9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <path d="M8 20h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <path d="M8.5 8.5a5 5 0 0 1 7 0M5.5 5.5a9 9 0 0 1 13 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    <circle cx="12" cy="9" r="2" fill="currentColor"/>
  </svg>`

const sensorSvg = () => `
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
    <path d="M12 3 21 12 12 21 3 12 12 3Z" fill="currentColor"/>
    <circle cx="12" cy="12" r="3" fill="#0f172a"/>
  </svg>`

const offlineSvg = () => `
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
    <circle cx="12" cy="12" r="7" fill="currentColor"/>
    <path d="M8 8l8 8" stroke="#0f172a" stroke-width="2" stroke-linecap="round"/>
  </svg>`

const alertSvg = () => `
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
    <path d="M12 3 22 20H2L12 3Z" fill="currentColor"/>
    <path d="M12 8v6" stroke="#0f172a" stroke-width="2.2" stroke-linecap="round"/>
    <circle cx="12" cy="17" r="1.2" fill="#0f172a"/>
  </svg>`

const formatTemperature = (temperature: number | null | undefined) => {
  if (temperature == null || Number.isNaN(temperature)) return 'N/D'
  return `${temperature.toFixed(1)}°C`
}

const createDeviceIcon = (device: MapAnimal, highlighted: boolean) => {
  const style = typeStyle(device.device_type, device.online)
  let color = device.outside_field ? '#ef4444' : style.color
  if (!device.outside_field && device.gps_fresh === 0) {
    color = '#64748b'
  }
  const batColor = batteryColor(device.battery_pct)
  return L.divIcon({
    className: '',
    html: `
      <div class="map-marker-c ${device.outside_field ? 'map-marker-c-alert' : ''} ${highlighted ? 'map-marker-c-highlight' : ''}" style="--mrk-color:${color};--mrk-bat:${batColor}">
        <span class="map-marker-c-icon" data-marker-part="icon">${device.outside_field ? alertSvg() : style.glyph}</span>
        <span class="map-marker-c-temp" data-marker-part="temp">${formatTemperature(device.temperature)}</span>
        <span class="map-marker-c-batt" data-marker-part="battery">
          <svg viewBox="0 0 12 8" width="12" height="8"><rect x="1" y="1" width="8" height="6" rx="1" fill="none" stroke="currentColor" stroke-width="1"/><rect x="10" y="2.5" width="1.5" height="3" rx="0.5" fill="currentColor"/><rect x="2" y="2" width="${device.battery_pct != null ? Math.max(0, Math.min(6, Math.round(device.battery_pct / 100 * 6))) : 0}" height="4" rx="0.5" fill="currentColor"/></svg>
          ${device.battery_pct != null ? Math.round(device.battery_pct) + '%' : '--'}
        </span>
      </div>`,
    iconSize: [48, 46],
    iconAnchor: [24, 46],
    tooltipAnchor: [0, -50],
    popupAnchor: [0, -50],
  })
}

const createGatewayIcon = (gw: MapGateway) => {
  const gwColor = gw.online > 0 ? '#3b82f6' : '#64748b'
  return L.divIcon({
    className: '',
    html: `
      <div class="map-marker-gw" style="--gw-color:${gwColor}">
        <span class="map-marker-gw-icon">
          <svg viewBox="0 0 24 24" width="18" height="18"><path d="M12 20V9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M8 20h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M8.5 8.5a5 5 0 0 1 7 0M5.5 5.5a9 9 0 0 1 13 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="9" r="2" fill="currentColor"/></svg>
        </span>
        <span class="map-marker-gw-label">${gw.name || gw.gateway_id}</span>
      </div>`,
    iconSize: [80, 32],
    iconAnchor: [40, 32],
    tooltipAnchor: [0, -36],
  })
}

/* ─── Sparkline ─── */
function SparkChart({ points, color, unit }: { points: { ts: string; value: number }[]; color: string; unit: string }) {
  const values = points.map(p => p.value)
  const { path, gridLines } = useMemo(() => {
    if (values.length < 2) return { path: '', gridLines: [] as number[] }
    const minV = Math.min(...values)
    const maxV = Math.max(...values)
    const span = Math.max(maxV - minV, 0.1)
    const w = 200; const h = 56; const pad = 8
    const step = (w - pad * 2) / (values.length - 1)
    const coords = values.map((v, idx) => {
      const x = pad + idx * step
      const y = pad + (maxV - v) / span * (h - pad * 2)
      return `${idx === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`
    }).join(' ')
    return { path: coords, gridLines: [minV, (minV + maxV) / 2, maxV] }
  }, [values])

  if (points.length < 2) return <p className="text-[10px] text-slate-500">Sin historial suficiente</p>

  return (
    <div className="space-y-1.5">
      <svg viewBox="0 0 200 56" className="h-14 w-full rounded-md" style={{ background: '#f1f5f9' }}>
        <defs>
          <linearGradient id="spark-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.18" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {gridLines.map((v, i) => {
          const y = 8 + (i / 2) * (56 - 16)
          return <path key={i} d={`M8 ${y.toFixed(1)} L192 ${y.toFixed(1)}`} stroke="#cbd5e1" strokeWidth="0.5" strokeDasharray="2 2" />
        })}
        <path d={`${path} L192 48 L8 48 Z`} fill="url(#spark-fill)" />
        <path d={path} fill="none" stroke={color} strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <div className="flex items-center justify-between text-[9px] text-slate-500">
        <span>{points[0].ts}</span>
        <span>{points[points.length - 1].ts}</span>
      </div>
    </div>
  )
}

/* ─── Tooltip hover: icono → datos completos ─── */
function IconTooltip({ device, enabled }: { device: MapAnimal; enabled: boolean }) {
  const { data: cons } = useQuery<ConsumptionResponse>({
    queryKey: ['consumption', device.device_id],
    queryFn: () => api.get(`/lora/devices/${encodeURIComponent(device.device_id)}/consumption?limit=48`).then(r => r.data),
    staleTime: 30_000,
    enabled,
  })

  return (
    <div className="text-xs space-y-2" style={{ color: '#0f172a', minWidth: 260 }}>
      <div className="flex items-center justify-between">
        <div>
          <strong className="text-sm">{device.name || device.device_uid}</strong>
          <p className="text-[10px] text-slate-500">{device.device_type}</p>
        </div>
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${device.is_online ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${device.is_online ? 'bg-emerald-500' : 'bg-slate-400'}`} />
          {device.is_online ? 'Online' : 'Offline'}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
        <p>Batería: <span style={{ color: batteryColor(device.battery_pct) }} className="font-semibold">{device.battery_pct != null ? Math.round(device.battery_pct) + '%' : '--'}</span></p>
        <p>Temp: <span className="font-semibold text-red-500">{formatTemperature(device.temperature)}</span></p>
        {cons && cons.samples >= 2 && (
          <>
            <p>Autonomía: <span className="font-semibold text-slate-700">{cons.autonomy_days != null ? `~${cons.autonomy_days} días` : '--'}</span></p>
            <p>Consumo diario: <span className="font-semibold text-slate-700">{cons.daily_mah.toFixed(1)} mAh</span></p>
            {cons.brownouts_detected > 0 && <p className="col-span-2 text-amber-600">Brownouts: {cons.brownouts_detected}</p>}
            {cons.last_charging === 1 && <p className="col-span-2 text-emerald-600">Cargando</p>}
          </>
        )}
          {device.field_name && <p>Campo: {device.field_name}</p>}
          {device.paddock_name && <p>Corral: {device.paddock_name}</p>}
        {device.outside_field && <p className="col-span-2 font-semibold text-red-600">Alarma: fuera del campo</p>}
        {device.last_seen && <p className="col-span-2 text-[10px] text-slate-400">Ultima: {new Date(device.last_seen).toLocaleString('es-AR')}</p>}
        <p className="col-span-2 text-[9px] text-slate-400">Coords: {device.lat.toFixed(6)}, {device.lon.toFixed(6)}</p>
      </div>
    </div>
  )
}

/* ─── Hover temp/bat → solo valor ─── */
function SimpleVal({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="text-xs" style={{ color: '#0f172a', minWidth: 120 }}>
      <span className="text-[10px] text-slate-500">{label}: </span>
      <span className="text-sm font-bold" style={color ? { color } : undefined}>{value}</span>
    </div>
  )
}

/* ─── Popup click: batería → gráfico ─── */
function BatteryPopup({ device, enabled }: { device: MapAnimal; enabled: boolean }) {
  const { data, isLoading } = useQuery<BatteryHistoryResponse>({
    queryKey: ['battery-history', device.device_id],
    queryFn: () => api.get(`/lora/devices/${encodeURIComponent(device.device_id)}/battery-history?limit=48`).then(r => r.data),
    staleTime: 30_000,
    enabled,
  })
  const points = (data?.points ?? []).map(p => ({ ts: p.ts, value: p.battery }))
  return (
    <div className="text-xs" style={{ color: '#0f172a', minWidth: 230 }}>
      <div className="flex items-center justify-between mb-2">
        <strong className="text-sm">Batería — {device.name || device.device_uid}</strong>
        <span style={{ color: batteryColor(device.battery_pct) }} className="text-[11px] font-bold">
          {device.battery_pct != null ? Math.round(device.battery_pct) + '%' : '--'}
        </span>
      </div>
      {isLoading && points.length === 0 ? <p className="text-[10px] text-slate-500">Cargando...</p> :
       <SparkChart points={points} color={batteryColor(device.battery_pct)} unit="%" />}
    </div>
  )
}

/* ─── Popup click: temperatura → gráfico ─── */
function TempPopup({ device, enabled }: { device: MapAnimal; enabled: boolean }) {
  const { data, isLoading } = useQuery<TemperatureHistoryResponse>({
    queryKey: ['temperature-history', device.device_id],
    queryFn: () => api.get(`/lora/devices/${encodeURIComponent(device.device_id)}/temperature-history?limit=48`).then(r => r.data),
    staleTime: 30_000,
    enabled,
  })
  const points = (data?.points ?? []).map(p => ({ ts: p.ts, value: p.temperature }))
  const last = points[points.length - 1]?.value ?? device.temperature
  return (
    <div className="text-xs" style={{ color: '#0f172a', minWidth: 230 }}>
      <div className="flex items-center justify-between mb-2">
        <strong className="text-sm">Temperatura — {device.name || device.device_uid}</strong>
        <span className="text-[11px] font-bold text-red-500">{formatTemperature(last)}</span>
      </div>
      {isLoading && points.length === 0 ? <p className="text-[10px] text-slate-500">Cargando...</p> :
       <SparkChart points={points} color="#ef4444" unit="°C" />}
    </div>
  )
}

function AutoFit({ data }: { data: MapData }) {
  const map = useMap()
  const fitted = useRef(false)
  useEffect(() => {
    const latlngs: [number, number][] = []

    // Animals
    data.animals.forEach(a => latlngs.push([a.lat, a.lon]))

    // Gateways
    data.gateways?.forEach(g => latlngs.push([g.lat, g.lon]))

    // Paddock/field polygons
    data.paddocks.features.forEach(feature => {
      const coords = feature.geometry?.coordinates as number[][][] | undefined
      coords?.[0]?.forEach(([lon, lat]) => {
        if (typeof lat === 'number' && typeof lon === 'number') latlngs.push([lat, lon])
      })
    })

    if (latlngs.length > 0 && !fitted.current) {
      map.fitBounds(L.latLngBounds(latlngs), { padding: [48, 48], maxZoom: 17 })
      fitted.current = true
    }
  }, [data, map])
  return null
}

function ResizeOnFullscreen({ fullscreen }: { fullscreen: boolean }) {
  const map = useMap()
  useEffect(() => {
    window.setTimeout(() => map.invalidateSize(), 120)
  }, [fullscreen, map])
  return null
}

interface LiveMapProps {
  data: MapData
  className?: string
  highlightDeviceId?: string | null
}

export default function LiveMap({ data, className = '', highlightDeviceId = null }: LiveMapProps) {
  const center = data.animals[0] ? [data.animals[0].lat, data.animals[0].lon] as [number, number] : [-31.6317, -60.6877] as [number, number]
  const shellRef = useRef<HTMLDivElement | null>(null)
  const [fullscreen, setFullscreen] = useState(false)
  const [hoveredDeviceId, setHoveredDeviceId] = useState<string | null>(null)
  const [hoveredPart, setHoveredPart] = useState<string | null>(null)
  const [clickedDeviceId, setClickedDeviceId] = useState<string | null>(null)
  const [clickedPart, setClickedPart] = useState<string | null>(null)
  const [editingGwId, setEditingGwId] = useState<string | null>(null)

  useEffect(() => {
    const onChange = () => setFullscreen(document.fullscreenElement === shellRef.current)
    document.addEventListener('fullscreenchange', onChange)
    return () => document.removeEventListener('fullscreenchange', onChange)
  }, [])

  const toggleFullscreen = async () => {
    if (!document.fullscreenElement) await shellRef.current?.requestFullscreen()
    else await document.exitFullscreen()
  }

  const getPart = (e: L.LeafletMouseEvent) =>
    (e.originalEvent.target as HTMLElement).closest('[data-marker-part]')?.getAttribute('data-marker-part') || null

  const handleMouseOver = (deviceId: string, e: L.LeafletMouseEvent) => {
    setHoveredDeviceId(deviceId)
    setHoveredPart(getPart(e))
  }

  const handleMouseOut = () => {
    setHoveredDeviceId(null)
    setHoveredPart(null)
  }

  const handleClick = (deviceId: string, e: L.LeafletMouseEvent) => {
    const p = getPart(e)
    if (p === 'temp' || p === 'battery') {
      setClickedDeviceId(deviceId)
      setClickedPart(p)
    }
  }

  return (
    <div ref={shellRef} className={`map-shell relative h-full w-full ${fullscreen ? 'is-fullscreen' : ''}`}>
      <button
        type="button"
        onClick={toggleFullscreen}
        className="map-fullscreen-btn"
        title={fullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
        aria-label={fullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
      >
        {fullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
      </button>
      <MapContainer
      center={center}
      zoom={15}
      className={`w-full h-full rounded-lg overflow-hidden ${className}`}
      zoomControl={true}
    >
      <LayersControl position="topright">
        <LayersControl.BaseLayer name="OpenStreetMap">
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer checked name="Satelite (Esri)">
          <TileLayer
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            attribution="&copy; Esri"
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
        <LayersControl.Overlay checked name="Campo y corrales">
          {data.paddocks.features.length > 0 && (
            <GeoJSON
              key={data.paddocks.features.map(f => String(f.properties.id)).join('-')}
              data={data.paddocks as any}
              style={(feature) => {
                const color = String(feature?.properties?.color || '#22c55e')
                const isField = feature?.properties?.kind === 'field'
                return {
                  color,
                  fillColor: color,
                  weight: isField ? 3 : 2,
                  fillOpacity: isField ? 0.08 : 0.24,
                  dashArray: isField ? undefined : '4 3',
                }
              }}
              onEachFeature={(feature, layer) => {
                const isField = feature.properties.kind === 'field'
                layer.bindPopup(
                  `<div style="color:#0f172a">
                    <strong>${feature.properties.name}</strong><br/>
                    Tipo: ${isField ? 'Campo' : 'Corral / sector'}<br/>
                    ${isField ? '' : `Estado: ${feature.properties.status}<br/>Animales: ${feature.properties.current_load}${feature.properties.max_capacity ? ' / ' + feature.properties.max_capacity : ''}`}
                  </div>`
                )
              }}
            />
          )}
        </LayersControl.Overlay>
      </LayersControl>

      <AutoFit data={data} />
      <ResizeOnFullscreen fullscreen={fullscreen} />

      {data.animals.map((animal) => {
        const isHovered = hoveredDeviceId === animal.device_id
        const part = isHovered ? hoveredPart : null
        const isClicked = clickedDeviceId === animal.device_id
        return (
          <Marker
            key={`${animal.device_id}-${animal.lat}-${animal.lon}-${animal.battery_pct}-${animal.is_online}`}
            position={[animal.lat, animal.lon]}
            icon={createDeviceIcon(animal, highlightDeviceId === animal.device_id)}
            draggable
            eventHandlers={{
              mouseover: (e) => handleMouseOver(animal.device_id, e),
              mouseout: handleMouseOut,
              click: (e) => handleClick(animal.device_id, e),
              dragend: (e) => {
                const pos = (e.target as any).getLatLng()
                api.put(`/lora/devices/${encodeURIComponent(animal.device_id)}`, {
                  lat: pos.lat,
                  lon: pos.lng,
                }).catch(() => {})
              },
            }}
          >
            <Tooltip sticky className="device-tooltip">
              {part === 'temp' ? <SimpleVal label="Temperatura" value={formatTemperature(animal.temperature)} color="#ef4444" /> :
               part === 'battery' ? <SimpleVal label="Batería" value={animal.battery_pct != null ? Math.round(animal.battery_pct) + '%' : '--'} color={batteryColor(animal.battery_pct)} /> :
               <IconTooltip device={animal} enabled={isHovered} />}
            </Tooltip>
            <Popup closeButton autoPan={false} className="device-tooltip">
              {isClicked && clickedPart === 'battery' ? <BatteryPopup device={animal} enabled /> :
               isClicked && clickedPart === 'temp' ? <TempPopup device={animal} enabled /> :
               null}
            </Popup>
          </Marker>
        )
      })}

      {data.gateways?.map((gw) => {
        const isEditing = editingGwId === gw.gateway_id
        const clientCount = gw.device_count ?? 0
        return (
          <Marker
            key={`gw-${gw.gateway_id}-${gw.lat}-${gw.lon}`}
            position={[gw.lat, gw.lon]}
            icon={createGatewayIcon(gw)}
            draggable={isEditing}
            eventHandlers={isEditing ? {
              dragend: (e) => {
                const pos = (e.target as any).getLatLng()
                api.put(`/lora/gateways/${encodeURIComponent(gw.gateway_id)}`, {
                  lat: pos.lat,
                  lon: pos.lng,
                }).then(() => setEditingGwId(null)).catch(() => {})
              },
            } : {
              click: () => setEditingGwId(gw.gateway_id),
            }}
          >
            <Tooltip sticky={!isEditing} permanent={isEditing} className="device-tooltip">
              <div className="text-xs" style={{ color: '#0f172a', minWidth: 180 }}>
                <strong className="text-sm">{gw.name || gw.gateway_id}</strong>
                <p className="text-[10px] text-slate-500">Gateway LoRa</p>
                <div className="mt-1.5 text-[11px] space-y-0.5">
                  <p>Estado: <span className={gw.online > 0 ? 'text-emerald-600 font-semibold' : 'text-red-500 font-semibold'}>{gw.online > 0 ? 'Online' : 'Offline'}</span></p>
                  <p>Clientes: <span className="font-semibold text-slate-700">{clientCount} dispositivo{clientCount !== 1 ? 's' : ''}</span></p>
                  {gw.battery_pct != null && <p>Batería: <span className="font-semibold" style={{ color: batteryColor(gw.battery_pct) }}>{Math.round(gw.battery_pct)}%</span>{gw.charging ? <span className="text-amber-500 ml-1">⚡</span> : ''}</p>}
                  {gw.last_seen && <p className="text-[10px] text-slate-400">Ultima: {new Date(gw.last_seen).toLocaleString('es-AR')}</p>}
                </div>
                <div className="mt-2 pt-2 border-t border-slate-200">
                  {isEditing ? (
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] text-amber-600 font-medium">Arrastrá para mover</span>
                      <button
                        onClick={(e) => { e.stopPropagation(); setEditingGwId(null) }}
                        className="text-[10px] px-2 py-0.5 rounded bg-slate-200 text-slate-600 hover:bg-slate-300"
                      >
                        Listo
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={(e) => { e.stopPropagation(); setEditingGwId(gw.gateway_id) }}
                      className="text-[10px] text-brand-500 hover:text-brand-400 underline"
                    >
                      Editar posición
                    </button>
                  )}
                </div>
              </div>
            </Tooltip>
          </Marker>
        )
      })}
      </MapContainer>
    </div>
  )
}
