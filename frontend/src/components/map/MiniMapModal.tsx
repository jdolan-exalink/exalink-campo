import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet'
import L from 'leaflet'
import { X, MapPin, Navigation } from 'lucide-react'

interface MiniMapModalProps {
  open: boolean
  onClose: () => void
  lat: number
  lon: number
  title?: string
  subtitle?: string
  batteryPct?: number | null
  temperature?: number | null
  lastSeen?: string | null
}

function Recenter({ lat, lon }: { lat: number; lon: number }) {
  const map = useMap()
  useEffect(() => {
    map.setView([lat, lon], map.getZoom(), { animate: true })
  }, [lat, lon, map])
  return null
}

const createIcon = (color: string) =>
  L.divIcon({
    className: '',
    html: `<div style="width:22px;height:22px;border-radius:999px;background:${color};border:3px solid white;box-shadow:0 2px 10px rgba(0,0,0,.55);display:grid;place-items:center;color:white;font-size:12px;font-weight:800">●</div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  })

export default function MiniMapModal({
  open, onClose, lat, lon, title, subtitle, batteryPct, temperature, lastSeen,
}: MiniMapModalProps) {
  if (!open) return null

  const batteryColor = (bat: number | null) => {
    if (bat == null) return '#94a3b8'
    if (bat <= 20) return '#ef4444'
    if (bat <= 50) return '#f59e0b'
    return '#22c55e'
  }

  return (
    <div
      className="fixed inset-0 z-[1200] flex items-center justify-center bg-black/70 p-4"
      onClick={onClose}
    >
      <div
        className="card w-full max-w-md overflow-hidden shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700">
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-white truncate flex items-center gap-2">
              <MapPin size={15} className="text-brand-400 flex-shrink-0" />
              {title || 'Ubicación'}
            </h3>
            {subtitle && <p className="text-xs text-slate-400 truncate mt-0.5">{subtitle}</p>}
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-surface-800 flex-shrink-0">
            <X size={18} />
          </button>
        </div>

        <div className="h-[280px] sm:h-[320px] w-full relative">
          <MapContainer
            center={[lat, lon]}
            zoom={17}
            className="w-full h-full"
            zoomControl={false}
            attributionControl={false}
          >
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
              attribution="&copy; Esri"
              maxZoom={19}
            />
            <TileLayer
              url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
              maxZoom={19}
            />
            <Marker position={[lat, lon]} icon={createIcon(batteryColor(batteryPct ?? null))} />
            <Recenter lat={lat} lon={lon} />
          </MapContainer>
          <div className="absolute bottom-2 right-2 bg-surface-950/80 backdrop-blur-sm rounded-md px-2 py-1 text-[10px] text-slate-400 font-mono pointer-events-none">
            {lat.toFixed(5)}, {lon.toFixed(5)}
          </div>
        </div>

        <div className="px-4 py-3 border-t border-surface-700 grid grid-cols-3 gap-3 text-xs">
          <div>
            <p className="text-[10px] text-slate-500 uppercase">Batería</p>
            <p className="font-semibold" style={{ color: batteryColor(batteryPct ?? null) }}>
              {batteryPct != null ? `${Math.round(batteryPct)}%` : '—'}
            </p>
          </div>
          <div>
            <p className="text-[10px] text-slate-500 uppercase">Temp</p>
            <p className="text-slate-200">{temperature != null ? `${temperature.toFixed(1)}°C` : '—'}</p>
          </div>
          <div>
            <p className="text-[10px] text-slate-500 uppercase">Última</p>
            <p className="text-slate-400 text-[11px]">
              {lastSeen ? new Date(lastSeen).toLocaleString('es-AR', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' }) : '—'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
