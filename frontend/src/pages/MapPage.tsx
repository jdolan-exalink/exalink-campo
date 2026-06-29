import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, Edit2, Plus, Trash2, X } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { Establishment, LoraDevice, LoraGateway, MapAnimal, MapData, MapGateway, Paddock } from '@/types'
import LiveMap from '@/components/map/LiveMap'
import PaddockMapEditor, { calcAreaHa, geoJsonToLeaflet, leafletToGeoJson, type LatLng } from '@/components/map/PaddockMapEditor'

const EMPTY: MapData = { animals: [], gateways: [], paddocks: { type: 'FeatureCollection', features: [] }, alerts: [] }
const DEFAULT_FIELD_COLOR = '#3b82f6'
const DEFAULT_PADDOCK_COLOR = '#22c55e'

const toMapAnimal = (device: LoraDevice, fieldLat?: number | null, fieldLon?: number | null): MapAnimal | null => {
  const lat = device.lat != null ? Number(device.lat) : (fieldLat ?? null)
  const lon = device.lon != null ? Number(device.lon) : (fieldLon ?? null)
  if (lat == null || lon == null) return null
  return {
    device_id: device.dev_addr,
    device_uid: device.name || device.dev_addr,
    animal_id: null,
    name: device.name,
    field_id: (device as any).field_id ?? null,
    field_name: (device as any).field_name ?? null,
    paddock_id: (device as any).paddock_id ?? null,
    paddock_name: (device as any).paddock_name ?? null,
    outside_field: Boolean((device as any).outside_field),
    gateway_id: device.gateway_id,
    lat,
    lon,
    battery_pct: device.battery_pct,
    temperature: device.temperature ?? null,
    is_online: device.online > 0,
    online: device.online,
    last_seen: device.last_seen,
    device_type: device.device_type || 'sensor',
    gps_fresh: device.gps_fresh,
  }
}

const fieldsToGeoJson = (fields: Establishment[], selectedId: string | null): MapData['paddocks'] => ({
  type: 'FeatureCollection',
  features: fields
    .filter(f => f.boundary != null && (!selectedId || f.id === selectedId))
    .map(f => ({
      type: 'Feature' as const,
      properties: {
        id: f.id,
        name: f.name,
        kind: 'field',
        status: 'Campo',
        current_load: 0,
        max_capacity: null,
        color: f.color || DEFAULT_FIELD_COLOR,
      },
      geometry: f.boundary!,
    })),
})

const paddocksToGeoJson = (paddocks: Paddock[], selectedFieldId: string | null): MapData['paddocks'] => ({
  type: 'FeatureCollection',
  features: paddocks
    .filter(p => p.polygon != null && (!selectedFieldId || p.establishment_id === selectedFieldId))
    .map(p => ({
      type: 'Feature' as const,
      properties: {
        id: p.id,
        name: p.name,
        kind: 'paddock',
        status: p.status,
        current_load: p.current_load,
        max_capacity: p.max_capacity,
        color: p.color || DEFAULT_PADDOCK_COLOR,
      },
      geometry: p.polygon!,
    })),
})

const mergeFeatures = (...collections: MapData['paddocks'][]): MapData['paddocks'] => ({
  type: 'FeatureCollection',
  features: collections.flatMap(c => c.features),
})

function polygonCenter(poly: Establishment['boundary'] | Paddock['polygon']): LatLng | undefined {
  const verts = geoJsonToLeaflet(poly as any)
  if (!verts.length) return undefined
  return [verts.reduce((s, [lat]) => s + lat, 0) / verts.length, verts.reduce((s, [, lon]) => s + lon, 0) / verts.length]
}

type EditorState =
  | { kind: 'field'; item?: Establishment | null }
  | { kind: 'paddock'; item?: Paddock | null; fieldId: string }

const sensorCenter = (animals: MapAnimal[]): LatLng | undefined => {
  const source = animals.find(a => a.is_online) || animals[0]
  return source ? [source.lat, source.lon] : undefined
}

export default function MapPage() {
  const qc = useQueryClient()
  const [searchParams] = useSearchParams()
  const highlightDevice = searchParams.get('highlight') || null
  const [selectedFieldId, setSelectedFieldId] = useState<string | null>(null)
  const [editor, setEditor] = useState<EditorState | null>(null)

  const { data: fields = [] } = useQuery<Establishment[]>({
    queryKey: ['fields'],
    queryFn: () => api.get('/establishments').then(r => r.data),
    refetchInterval: 10_000,
  })
  const { data: paddocks = [] } = useQuery<Paddock[]>({
    queryKey: ['paddocks'],
    queryFn: () => api.get('/paddocks').then(r => r.data),
    refetchInterval: 10_000,
  })
  const { data: devicesData } = useQuery<{ devices: LoraDevice[] }>({
    queryKey: ['lora-devices-map'],
    queryFn: () => api.get('/lora/devices').then(r => r.data),
    refetchInterval: 3_000,
  })

  const { data: gwData } = useQuery<{ gateways: LoraGateway[] }>({
    queryKey: ['lora-gateways-map'],
    queryFn: () => api.get('/lora/gateways').then(r => r.data),
    refetchInterval: 15_000,
  })

  const activeField = useMemo(() => fields.find(f => f.id === selectedFieldId) || fields[0] || null, [fields, selectedFieldId])
  const effectiveFieldId = selectedFieldId || activeField?.id || null

  const mapData = useMemo<MapData>(() => {
    const activeHasBoundary = Boolean(activeField?.boundary)
    const animals = (devicesData?.devices ?? [])
      .map(d => toMapAnimal(d, activeField?.lat, activeField?.lon))
      .filter((item): item is MapAnimal => item !== null)
      .map(item => ({
        ...item,
        outside_field: Boolean(
          item.outside_field ||
          (activeHasBoundary && effectiveFieldId && item.field_id !== effectiveFieldId)
        ),
      }))
    const gateways: MapGateway[] = (gwData?.gateways ?? [])
      .map(g => ({
        gateway_id: g.gateway_id,
        name: g.name,
        lat: g.lat != null ? Number(g.lat) : (activeField?.lat ?? -31.6317),
        lon: g.lon != null ? Number(g.lon) : (activeField?.lon ?? -60.6877),
        online: g.online,
        battery_pct: g.battery_pct,
        charging: g.charging,
        temperature: g.temperature,
        humidity: g.humidity,
        last_seen: g.last_seen,
        device_count: g.device_count,
      }))
    return {
      ...EMPTY,
      animals,
      gateways,
      paddocks: mergeFeatures(
        fieldsToGeoJson(fields, effectiveFieldId),
        paddocksToGeoJson(paddocks, effectiveFieldId),
      ),
    }
  }, [devicesData, gwData, fields, paddocks, effectiveFieldId, activeField])

  const deleteField = useMutation({
    mutationFn: (id: string) => api.delete(`/establishments/${id}`),
    onSuccess: () => { toast.success('Campo eliminado'); setSelectedFieldId(null); qc.invalidateQueries({ queryKey: ['fields'] }); qc.invalidateQueries({ queryKey: ['paddocks'] }) },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'No se pudo eliminar el campo'),
  })
  const deletePaddock = useMutation({
    mutationFn: (id: string) => api.delete(`/paddocks/${id}`),
    onSuccess: () => { toast.success('Corral eliminado'); qc.invalidateQueries({ queryKey: ['paddocks'] }) },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'No se pudo eliminar el corral'),
  })

  const fieldPaddocks = paddocks.filter(p => !effectiveFieldId || p.establishment_id === effectiveFieldId)
  const outsideSelectedField = mapData.animals.filter(a => a.outside_field)

  return (
    <div className="h-full p-4 flex flex-col gap-3">
      <div className="flex items-center gap-2 overflow-x-auto rounded-lg border border-surface-700 bg-surface-900 p-2">
        {fields.map(field => (
          <button
            key={field.id}
            onClick={() => setSelectedFieldId(field.id)}
            className={`shrink-0 rounded-md border px-3 py-2 text-sm transition-colors ${effectiveFieldId === field.id ? 'border-brand-400 bg-brand-600/20 text-white' : 'border-surface-700 bg-surface-800 text-slate-300 hover:border-surface-500'}`}
          >
            <span className="mr-2 inline-block h-3 w-3 rounded-sm border border-white/60 align-[-1px]" style={{ backgroundColor: field.color || DEFAULT_FIELD_COLOR }} />
            {field.name}
          </button>
        ))}
        <button onClick={() => setEditor({ kind: 'field', item: null })} className="btn-secondary shrink-0 text-xs"><Plus size={14} /> Campo</button>
        {activeField && <button onClick={() => setEditor({ kind: 'field', item: activeField })} className="btn-secondary shrink-0 text-xs"><Edit2 size={14} /> Editar campo</button>}
        {activeField && <button onClick={() => confirm(`Eliminar campo ${activeField.name} y sus corrales?`) && deleteField.mutate(activeField.id)} className="btn-danger shrink-0 text-xs"><Trash2 size={14} /> Borrar campo</button>}
        {activeField && <button onClick={() => setEditor({ kind: 'paddock', item: null, fieldId: activeField.id })} className="btn-primary shrink-0 text-xs"><Plus size={14} /> Corral</button>}
      </div>

      {outsideSelectedField.length > 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          <AlertTriangle size={16} />
          {outsideSelectedField.length === 1 ? 'Hay 1 sensor fuera del campo seleccionado.' : `Hay ${outsideSelectedField.length} sensores fuera del campo seleccionado.`}
        </div>
      )}

      <div className="map-workspace min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          <LiveMap data={mapData} className="h-full" highlightDeviceId={highlightDevice} />
        </div>
        <aside className="paddock-rail" tabIndex={0} aria-label="Corrales y sectores">
          <div className="paddock-rail-collapsed" aria-hidden="true">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">Corrales</span>
            <div className="paddock-rail-swatches">
              {fieldPaddocks.slice(0, 8).map(p => (
                <span key={p.id} style={{ backgroundColor: p.color || DEFAULT_PADDOCK_COLOR }} />
              ))}
              {fieldPaddocks.length === 0 && <span className="empty" />}
            </div>
            <span className="rounded-md border border-surface-600 bg-surface-800 px-2 py-1 text-xs font-bold text-white">{fieldPaddocks.length}</span>
          </div>
          <div className="paddock-rail-content">
            <h2 className="mb-3 text-sm font-semibold text-white">Corrales / sectores</h2>
            <div className="space-y-2">
              {fieldPaddocks.map(p => (
                <div key={p.id} className="rounded-md border border-surface-700 bg-surface-800 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="flex min-w-0 items-center gap-2 text-sm font-medium text-white"><span className="inline-block h-5 w-5 shrink-0 rounded border border-white/60" style={{ backgroundColor: p.color || DEFAULT_PADDOCK_COLOR }} /><span className="truncate">{p.name}</span></p>
                      <p className="mt-1 text-xs text-slate-400">{p.area_ha ? `${p.area_ha.toFixed(1)} ha` : 'Sin area'} · {p.polygon ? 'con poligono' : 'sin poligono'}</p>
                    </div>
                    <div className="flex gap-1">
                      <button className="rounded p-1.5 text-slate-400 hover:bg-surface-700 hover:text-brand-400" onClick={() => setEditor({ kind: 'paddock', item: p, fieldId: p.establishment_id })}><Edit2 size={13} /></button>
                      <button className="rounded p-1.5 text-slate-400 hover:bg-danger/10 hover:text-danger" onClick={() => confirm(`Eliminar corral ${p.name}?`) && deletePaddock.mutate(p.id)}><Trash2 size={13} /></button>
                    </div>
                  </div>
                </div>
              ))}
              {fieldPaddocks.length === 0 && <p className="rounded-md border border-dashed border-surface-700 p-4 text-center text-sm text-slate-500">Este campo todavia no tiene corrales.</p>}
            </div>
          </div>
        </aside>
      </div>

      {editor && (
        <FieldPaddockEditor
          editor={editor}
          fields={fields}
          paddocks={paddocks}
          sensors={mapData.animals}
          onClose={() => setEditor(null)}
          onSaved={() => { setEditor(null); qc.invalidateQueries({ queryKey: ['fields'] }); qc.invalidateQueries({ queryKey: ['paddocks'] }) }}
        />
      )}
    </div>
  )
}

function FieldPaddockEditor({ editor, fields, paddocks, sensors, onClose, onSaved }: {
  editor: EditorState
  fields: Establishment[]
  paddocks: Paddock[]
  sensors: MapAnimal[]
  onClose: () => void
  onSaved: () => void
}) {
  const isField = editor.kind === 'field'
  const item = editor.item ?? null
  const [name, setName] = useState(item?.name ?? '')
  const [color, setColor] = useState(item?.color ?? (isField ? DEFAULT_FIELD_COLOR : DEFAULT_PADDOCK_COLOR))
  const [vertices, setVertices] = useState<LatLng[]>(geoJsonToLeaflet((isField ? (item as Establishment | null)?.boundary : (item as Paddock | null)?.polygon) as any))
  const [saving, setSaving] = useState(false)
  const field = isField ? null : fields.find(f => f.id === editor.fieldId)
  const center = polygonCenter(field?.boundary ?? null) || sensorCenter(sensors) || (fields[0] ? [fields[0].lat ?? -31.6317, fields[0].lon ?? -60.6877] as LatLng : undefined)

  const save = async () => {
    if (!name.trim()) { toast.error('El nombre es obligatorio'); return }
    if (vertices.length < 3) { toast.error('Dibuja al menos 3 puntos'); return }
    setSaving(true)
    try {
      if (isField) {
        const payload = { name: name.trim(), color, boundary: leafletToGeoJson(vertices), lat: vertices[0][0], lon: vertices[0][1] }
        if (item) await api.put(`/establishments/${item.id}`, payload)
        else await api.post('/establishments', payload)
      } else {
        const payload = { name: name.trim(), color, polygon: leafletToGeoJson(vertices), area_ha: calcAreaHa(vertices), establishment_id: editor.fieldId }
        if (item) await api.put(`/paddocks/${item.id}`, payload)
        else await api.post('/paddocks', payload)
      }
      toast.success(isField ? 'Campo guardado' : 'Corral guardado')
      onSaved()
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo guardar')
    } finally {
      setSaving(false)
    }
  }

  const others = isField
    ? []
    : paddocks.filter(p => p.id !== item?.id && p.establishment_id === editor.fieldId)

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/70 p-4" onClick={onClose}>
      <div className="flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-xl border border-surface-700 bg-surface-950 shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-surface-700 px-5 py-4">
          <div>
            <h2 className="text-sm font-semibold text-white">{item ? 'Editar' : 'Crear'} {isField ? 'campo' : 'corral / sector'}</h2>
            {!isField && field && <p className="mt-1 text-xs text-slate-400">Dentro de: {field.name}</p>}
          </div>
          <div className="flex items-center gap-2">
            <button className="btn-primary px-3 py-1.5 text-xs" onClick={save} disabled={saving}>{saving ? 'Guardando...' : 'Guardar'}</button>
            <button onClick={onClose} className="rounded p-1 text-slate-400 hover:bg-surface-800 hover:text-white"><X size={18} /></button>
          </div>
        </div>
        <div className="grid min-h-0 flex-1 grid-cols-[280px_1fr] overflow-hidden">
          <div className="space-y-4 border-r border-surface-700 p-4">
            <label className="block text-xs font-semibold uppercase text-slate-400">Nombre</label>
            <input className="input" value={name} onChange={e => setName(e.target.value)} placeholder={isField ? 'Campo Norte' : 'Corral 1'} autoFocus />
            <label className="block text-xs font-semibold uppercase text-slate-400">Color</label>
            <div className="grid grid-cols-[44px_1fr] gap-2">
              <input type="color" value={color} onChange={e => setColor(e.target.value)} className="h-10 w-11 rounded border border-surface-700 bg-surface-900 p-1" />
              <select className="input" value={color} onChange={e => setColor(e.target.value)}>
                <option value="#3b82f6">Azul</option><option value="#22c55e">Verde</option><option value="#f59e0b">Amarillo</option><option value="#ef4444">Rojo</option><option value="#a855f7">Violeta</option><option value="#14b8a6">Turquesa</option><option value="#64748b">Gris</option>
              </select>
            </div>
            <div className="rounded-lg border border-surface-700 bg-surface-900 p-3 text-xs text-slate-400">
              {vertices.length >= 3 ? `${vertices.length} puntos · ${calcAreaHa(vertices).toFixed(1)} ha` : 'Dibuja el poligono en el mapa'}
            </div>
          </div>
          <div className="min-h-0 overflow-auto p-4">
            <PaddockMapEditor vertices={vertices} onVerticesChange={setVertices} otherPaddocks={others} sensors={sensors} center={center} color={color} mapHeight={460} />
          </div>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-surface-700 px-5 py-4">
          <button className="btn-secondary" onClick={onClose}>Cancelar</button>
          <button className="btn-primary" onClick={save} disabled={saving}>{saving ? 'Guardando...' : 'Guardar'}</button>
        </div>
      </div>
    </div>
  )
}
