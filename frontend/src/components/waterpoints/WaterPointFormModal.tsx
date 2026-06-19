import { useState, useEffect, useMemo } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { X, Loader2, Droplets } from 'lucide-react'
import toast from 'react-hot-toast'
import {
  MapContainer, TileLayer, Marker, Circle, Polygon, Tooltip, useMap, useMapEvents, LayersControl,
} from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import api from '@/lib/api'
import type { WaterPoint, Establishment, Paddock, Animal, AnimalListResponse, LoraDevice } from '@/types'
import { geoJsonToLeaflet, type LatLng } from '@/components/map/PaddockMapEditor'

const schema = z.object({
  name: z.string().min(1, 'El nombre es obligatorio'),
  type: z.enum(['water', 'trough']).default('water'),
  radius_m: z.coerce.number().positive('Debe ser mayor a 0').max(2000, 'Máx 2000 m'),
  capacity_l: z.coerce.number().positive().optional().or(z.literal('')),
  notes: z.string().optional(),
  is_active: z.boolean().default(true),
})
type FormValues = z.infer<typeof schema>

interface Props {
  isOpen: boolean
  onClose: () => void
  waterPoint?: WaterPoint | null
  establishmentId?: string | null
}

const createIcon = () =>
  L.divIcon({
    className: '',
    html: `<div style="width:24px;height:24px;border-radius:999px;background:#38bdf8;border:3px solid white;box-shadow:0 2px 12px rgba(0,0,0,.6);display:grid;place-items:center;color:white"><svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 2.5S5 11 5 15.5A7 7 0 0 0 19 15.5C19 11 12 2.5 12 2.5Z"/></svg></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  })

const createDeviceIcon = () =>
  L.divIcon({
    className: '',
    html: `<div style="width:14px;height:14px;border-radius:999px;background:#22c55e;border:2px solid white;box-shadow:0 1px 6px rgba(0,0,0,.7)"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })

function ClickHandler({ onClick }: { onClick: (lat: number, lon: number) => void }) {
  useMapEvents({
    click(e) { onClick(e.latlng.lat, e.latlng.lng) },
  })
  return null
}

function FitField({ vertices, position, devices }: { vertices: LatLng[]; position: LatLng | null; devices: { lat: number; lon: number }[] }) {
  const map = useMap()
  useEffect(() => {
    if (position) return
    if (vertices.length >= 3) {
      const bounds = L.latLngBounds(vertices as [number, number][])
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 18 })
    } else if (devices.length > 0) {
      const pts = devices.map(d => [d.lat, d.lon] as [number, number])
      map.fitBounds(L.latLngBounds(pts), { padding: [50, 50], maxZoom: 17 })
    } else if (vertices.length === 1) {
      map.setView(vertices[0], 17, { animate: true })
    }
  }, [vertices, position, devices.length]) // eslint-disable-line
  return null
}

export default function WaterPointFormModal({ isOpen, onClose, waterPoint, establishmentId }: Props) {
  const qc = useQueryClient()
  const [position, setPosition] = useState<LatLng | null>(null)
  const [selectedEstId, setSelectedEstId] = useState<string | null>(null)

  const { data: establishments = [] } = useQuery<Establishment[]>({
    queryKey: ['establishments'],
    queryFn: () => api.get('/establishments').then(r => r.data),
    enabled: isOpen,
  })
  const { data: paddocks = [] } = useQuery<Paddock[]>({
    queryKey: ['paddocks'],
    queryFn: () => api.get('/paddocks').then(r => r.data),
    enabled: isOpen,
  })

  const { data: animalsData } = useQuery<AnimalListResponse>({
    queryKey: ['animals-for-waterpoint-modal'],
    queryFn: () => api.get('/animals?page_size=500').then(r => r.data),
    enabled: isOpen,
  })

  const { data: loraData } = useQuery<{ devices: LoraDevice[] }>({
    queryKey: ['lora-devices-for-waterpoint-modal'],
    queryFn: () => api.get('/lora/devices').then(r => r.data),
    enabled: isOpen,
  })

  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  useEffect(() => {
    if (!isOpen) return
    if (waterPoint) {
      reset({
        name: waterPoint.name,
        type: waterPoint.type,
        radius_m: waterPoint.radius_m,
        capacity_l: waterPoint.capacity_l ?? '',
        notes: waterPoint.notes ?? '',
        is_active: waterPoint.is_active,
      })
      setPosition([waterPoint.lat, waterPoint.lon])
      setSelectedEstId(waterPoint.establishment_id)
    } else {
      reset({ type: 'water', radius_m: 30, is_active: true })
      setPosition(null)
      setSelectedEstId(establishmentId || establishments[0]?.id || null)
    }
  }, [isOpen, waterPoint?.id]) // eslint-disable-line

  const saveMutation = useMutation({
    mutationFn: async (data: FormValues) => {
      const estId = selectedEstId || establishments[0]?.id
      if (!estId) throw new Error('No hay establecimientos registrados')
      if (!position) throw new Error('Marcá la ubicación en el mapa')
      const payload = {
        name: data.name,
        type: data.type,
        radius_m: data.radius_m,
        capacity_l: data.capacity_l || null,
        notes: data.notes || null,
        is_active: data.is_active,
        establishment_id: estId,
        lat: position[0],
        lon: position[1],
      }
      return waterPoint
        ? api.put(`/water-points/${waterPoint.id}`, payload)
        : api.post('/water-points', payload)
    },
    onSuccess: () => {
      toast.success(waterPoint ? 'Punto de agua actualizado' : 'Punto de agua creado')
      qc.invalidateQueries({ queryKey: ['water-points'] })
      qc.invalidateQueries({ queryKey: ['water-points-map'] })
      onClose()
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || err.message || 'Error al guardar'),
  })

  const selectedEst = establishments.find(e => e.id === selectedEstId) || null
  const estVertices = useMemo<LatLng[]>(() => {
    if (!selectedEst?.boundary) return []
    return geoJsonToLeaflet(selectedEst.boundary)
  }, [selectedEstId, selectedEst]) // eslint-disable-line

  const fieldDevices = useMemo<{ id: string; lat: number; lon: number; earTag: string }[]>(() => {
    const items: { id: string; lat: number; lon: number; earTag: string }[] = []
    const seen = new Set<string>()

    if (animalsData?.items) {
      for (const a of animalsData.items) {
        if (a.last_lat == null || a.last_lon == null) continue
        if (selectedEstId && a.establishment_id !== selectedEstId) continue
        const key = a.device_uid || a.id
        if (seen.has(key)) continue
        seen.add(key)
        items.push({ id: a.id, lat: a.last_lat, lon: a.last_lon, earTag: a.ear_tag })
      }
    }

    if (loraData?.devices) {
      for (const d of loraData.devices) {
        const lat = d.lat != null ? Number(d.lat) : null
        const lon = d.lon != null ? Number(d.lon) : null
        if (lat == null || lon == null) continue
        const fieldId = (d as any).field_id as string | undefined
        if (selectedEstId && fieldId !== selectedEstId) continue
        const key = d.dev_addr
        if (seen.has(key)) continue
        seen.add(key)
        items.push({ id: d.dev_addr, lat, lon, earTag: d.name || d.dev_addr })
      }
    }

    return items
  }, [animalsData, loraData, selectedEstId])

  if (!isOpen) return null

  const estCenter: LatLng | undefined =
    selectedEst?.lat != null
      ? [selectedEst.lat!, selectedEst.lon!]
      : (estVertices.length >= 1
          ? [estVertices.reduce((s, [y]) => s + y, 0) / estVertices.length,
             estVertices.reduce((s, [, x]) => s + x, 0) / estVertices.length]
          : undefined)
  const mapCenter = position ?? estCenter ?? [-31.6317, -60.6877]
  const radius = watch('radius_m') || waterPoint?.radius_m || 30
  const fieldPaddocks = paddocks.filter(p => p.establishment_id === selectedEstId)

  return (
    <div
      style={{ position: 'fixed', inset: 0, zIndex: 9999, background: 'rgba(0,0,0,0.7)', display: 'flex', alignItems: 'stretch', justifyContent: 'center', padding: 0 }}
      className="sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        className="w-full max-w-[1000px] flex flex-col overflow-hidden rounded-none sm:rounded-2xl"
        style={{ background: '#0f172a', border: '1px solid #334155', boxShadow: '0 25px 60px rgba(0,0,0,0.8)', maxHeight: '100vh' }}
      >
        <div className="flex items-center justify-between px-4 sm:px-6 py-3 sm:py-4 border-b border-surface-700 flex-shrink-0">
          <div className="min-w-0 flex items-center gap-2">
            <Droplets size={16} className="text-sky-400 flex-shrink-0" />
            <div className="min-w-0">
              <h2 className="text-sm sm:text-base font-semibold text-white truncate" style={{ margin: 0 }}>
                {waterPoint ? `Editar: ${waterPoint.name}` : 'Nuevo punto de agua'}
              </h2>
              <p className="text-xs text-slate-400 mt-0.5 hidden sm:block">
                Elegí el campo y hacé clic en el mapa para ubicar el punto
              </p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-surface-800 flex-shrink-0">
            <X size={18} />
          </button>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto flex flex-col lg:grid lg:grid-cols-[280px_1fr]">
          <div className="p-4 sm:p-5 space-y-4 flex flex-col gap-4 lg:border-r lg:border-surface-700 lg:overflow-y-auto">
            <Field label="Campo *" error={errors.name ? undefined : (!selectedEstId ? 'Seleccioná un campo' : undefined)}>
              <select
                value={selectedEstId ?? ''}
                onChange={e => { setSelectedEstId(e.target.value); setPosition(null) }}
                className="input"
              >
                <option value="" disabled>Seleccionar campo…</option>
                {establishments.map(e => (
                  <option key={e.id} value={e.id}>{e.name}</option>
                ))}
              </select>
            </Field>

            <Field label="Nombre *" error={errors.name?.message}>
              <input {...register('name')} className="input" placeholder="Bebedero Norte" autoFocus />
            </Field>

            <Field label="Tipo">
              <select {...register('type')} className="input">
                <option value="water">Aguada natural</option>
                <option value="trough">Bebedero</option>
              </select>
            </Field>

            <Field label="Radio de detección (m)" error={errors.radius_m?.message}>
              <input type="number" step="1" min="1" max="2000" {...register('radius_m')} className="input" placeholder="30" />
            </Field>

            <Field label="Capacidad (L)">
              <input type="number" step="1" min="0" {...register('capacity_l')} className="input" placeholder="500" />
            </Field>

            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" {...register('is_active')} style={{ width: '16px', height: '16px', accentColor: '#38bdf8' }} />
              <span className="text-sm text-slate-300">Activo</span>
            </label>

            <Field label="Notas">
              <textarea {...register('notes')} className="input" style={{ resize: 'none' }} rows={3} placeholder="Observaciones..." />
            </Field>

            <div className="rounded-lg p-3 text-xs"
              style={{
                background: position ? 'rgba(56,189,248,0.06)' : '#1e293b',
                border: `1px solid ${position ? 'rgba(56,189,248,0.25)' : '#334155'}`,
              }}>
              <p className="uppercase tracking-wide text-slate-500 mb-1" style={{ fontSize: '11px' }}>Ubicación</p>
              {position ? (
                <p className="text-sky-300 font-mono" style={{ margin: 0 }}>
                  {position[0].toFixed(6)}, {position[1].toFixed(6)}
                </p>
              ) : (
                <p className="text-slate-500" style={{ margin: 0 }}>Sin ubicación — hacé clic en el mapa</p>
              )}
            </div>
          </div>

          <div className="p-2 sm:p-4 min-h-[300px] lg:min-h-0">
            <MapContainer
              center={mapCenter}
              zoom={16}
              className="w-full h-full rounded-lg overflow-hidden"
              style={{ height: '100%', minHeight: 300 }}
            >
              <LayersControl position="topright">
                <LayersControl.BaseLayer name="OpenStreetMap">
                  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; OpenStreetMap' maxZoom={19} />
                </LayersControl.BaseLayer>
                <LayersControl.BaseLayer checked name="Satelite (Esri)">
                  <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" attribution="&copy; Esri" maxZoom={19} />
                </LayersControl.BaseLayer>
              </LayersControl>

              <ClickHandler onClick={(lat, lon) => setPosition([lat, lon])} />
              <FitField vertices={estVertices} position={position} devices={fieldDevices} />

              {/* Dispositivos existentes en el campo */}
              {fieldDevices.map(d => (
                <Marker key={d.id} position={[d.lat, d.lon]} icon={createDeviceIcon()} zIndexOffset={-100}>
                  <Tooltip direction="top" offset={[0, -8]} className="device-tooltip">
                    <div className="text-xs" style={{ color: '#0f172a', minWidth: 80 }}>
                      <strong className="text-[11px]">{d.earTag}</strong>
                    </div>
                  </Tooltip>
                </Marker>
              ))}

              {/* Polígono del campo seleccionado */}
              {estVertices.length >= 3 && (
                <Polygon
                  positions={estVertices as any}
                  pathOptions={{ color: selectedEst?.color || '#3b82f6', fillColor: selectedEst?.color || '#3b82f6', fillOpacity: 0.06, weight: 2.5 }}
                />
              )}

              {/* Potreros del campo seleccionado */}
              {fieldPaddocks.map(p => {
                const verts = geoJsonToLeaflet(p.polygon)
                if (verts.length < 3) return null
                return (
                  <Polygon key={p.id} positions={verts as any} pathOptions={{ color: p.color || '#22c55e', fillColor: p.color || '#22c55e', fillOpacity: 0.08, weight: 1.5, dashArray: '4 3' }} />
                )
              })}

              {position && (
                <>
                  <Marker
                    position={position}
                    icon={createIcon()}
                    draggable
                    eventHandlers={{ dragend: (e) => { const p = (e.target as any).getLatLng(); setPosition([p.lat, p.lng]) } }}
                  />
                  <Circle center={position} radius={Number(radius)} pathOptions={{ color: '#38bdf8', fillColor: '#38bdf8', fillOpacity: 0.12, weight: 1.5, dashArray: '4 3' }} />
                </>
              )}
            </MapContainer>
          </div>
        </div>

        <div className="flex items-center justify-between gap-2 px-4 sm:px-6 py-3 sm:py-4 border-t border-surface-700 flex-shrink-0">
          <p className="text-xs text-slate-500 hidden sm:block">
            {position ? `Ubicación: ${position[0].toFixed(5)}, ${position[1].toFixed(5)} · radio ${radius} m` : 'Marcá la ubicación en el mapa'}
          </p>
          <div className="flex gap-2 ml-auto">
            <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
            <button type="button" onClick={handleSubmit(d => saveMutation.mutate(d))} disabled={saveMutation.isPending} className="btn-primary">
              {saveMutation.isPending && <Loader2 size={14} className="animate-spin" />}
              {waterPoint ? 'Guardar' : 'Crear'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: '11px', fontWeight: 500, color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</label>
      {children}
      {error && <p style={{ margin: '4px 0 0', fontSize: '11px', color: '#f87171' }}>{error}</p>}
    </div>
  )
}
