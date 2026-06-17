import { useState, useEffect, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'
import {
  MapContainer, TileLayer, Polygon, CircleMarker,
  Marker, useMapEvents, useMap,
} from 'react-leaflet'
import L from 'leaflet'
import type { MapAnimal, Paddock } from '@/types'

export type LatLng = [number, number]
type Mode = 'idle' | 'drawing' | 'editing'

// ── Geo utils ────────────────────────────────────────────────────────────────

export function calcAreaHa(v: LatLng[]): number {
  if (v.length < 3) return 0
  const n = v.length
  const cosLat = Math.cos((v.reduce((s, [y]) => s + y, 0) / n) * (Math.PI / 180))
  let a = 0
  for (let i = 0; i < n; i++) {
    const [y1, x1] = v[i], [y2, x2] = v[(i + 1) % n]
    a += (x2 - x1) * (y2 + y1)
  }
  return Math.abs(a / 2) * (111320 ** 2) * cosLat / 10000
}

export function geoJsonToLeaflet(polygon: Paddock['polygon']): LatLng[] {
  if (!polygon?.coordinates?.[0]) return []
  return polygon.coordinates[0].slice(0, -1).map(([lon, lat]) => [lat, lon] as LatLng)
}

export function leafletToGeoJson(v: LatLng[]) {
  if (v.length < 3) return null
  const c = v.map(([lat, lon]) => [lon, lat])
  return { type: 'Polygon' as const, coordinates: [[...c, c[0]]] }
}

// ── Toolbar rendered via Leaflet Control (guaranteed on top of tiles) ─────────

function ToolbarControl({
  mode, vertices, area,
  onDraw, onEdit, onUndo, onClear, onFinish,
}: {
  mode: Mode; vertices: LatLng[]; area: number
  onDraw: () => void; onEdit: () => void
  onUndo: () => void; onClear: () => void; onFinish: () => void
}) {
  const map = useMap()
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    // Create a plain Leaflet control
    const div = L.DomUtil.create('div', 'leaflet-control leaflet-bar')
    div.style.cssText = `
      background: #0f172a;
      border: 2px solid #3b82f6 !important;
      border-radius: 10px;
      padding: 8px;
      min-width: 220px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.8);
      pointer-events: auto;
    `
    L.DomEvent.disableClickPropagation(div)
    L.DomEvent.disableScrollPropagation(div)
    containerRef.current = div

    // Add to top-left pane
    const pane = map.getContainer().querySelector('.leaflet-top.leaflet-left')
    if (pane) pane.appendChild(div)

    return () => { div.remove() }
  }, [map])

  if (!containerRef.current) return null

  const statusColor =
    mode === 'drawing' ? '#93c5fd' :
    mode === 'editing' ? '#fcd34d' :
    vertices.length >= 3 ? '#4ade80' : '#94a3b8'

  const statusMsg =
    mode === 'drawing' ? (vertices.length < 3
      ? `Clic en el mapa para agregar puntos (${vertices.length}/3)`
      : `${vertices.length} puntos · presioná Finalizar`)
    : mode === 'editing'
      ? 'Arrastrá los puntos · Clic derecho para borrar'
      : vertices.length >= 3
        ? `✓ ${vertices.length} vértices · ~${area.toFixed(1)} ha`
        : 'Presioná "Dibujar" para comenzar'

  return createPortal(
    <div>
      {/* Buttons row */}
      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '6px' }}>
        <button
          onClick={onDraw}
          style={{
            background: mode === 'drawing' ? '#2563eb' : '#1e293b',
            color: mode === 'drawing' ? 'white' : '#94a3b8',
            border: `1px solid ${mode === 'drawing' ? '#3b82f6' : '#334155'}`,
            borderRadius: '6px', padding: '5px 10px',
            fontSize: '11px', fontWeight: 600, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: '4px',
          }}
        >
          ✏️ {mode === 'drawing' ? 'Cancelar' : vertices.length > 0 ? 'Redibujar' : 'Dibujar'}
        </button>

        <button
          onClick={onEdit}
          disabled={vertices.length < 3}
          style={{
            background: mode === 'editing' ? '#92400e' : '#1e293b',
            color: mode === 'editing' ? '#fde68a' : vertices.length < 3 ? '#475569' : '#94a3b8',
            border: `1px solid ${mode === 'editing' ? '#f59e0b' : '#334155'}`,
            borderRadius: '6px', padding: '5px 10px',
            fontSize: '11px', fontWeight: 600, cursor: vertices.length < 3 ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', gap: '4px',
          }}
        >
          🔵 {mode === 'editing' ? 'Listo' : 'Editar'}
        </button>

        <button
          onClick={onUndo}
          disabled={vertices.length === 0}
          style={{
            background: '#1e293b', color: vertices.length === 0 ? '#475569' : '#94a3b8',
            border: '1px solid #334155', borderRadius: '6px', padding: '5px 8px',
            fontSize: '11px', cursor: vertices.length === 0 ? 'not-allowed' : 'pointer',
          }}
        >
          ↩ Deshacer
        </button>

        <button
          onClick={onClear}
          disabled={vertices.length === 0}
          style={{
            background: '#1e293b', color: vertices.length === 0 ? '#475569' : '#f87171',
            border: `1px solid ${vertices.length === 0 ? '#334155' : '#ef444440'}`,
            borderRadius: '6px', padding: '5px 8px',
            fontSize: '11px', cursor: vertices.length === 0 ? 'not-allowed' : 'pointer',
          }}
        >
          🗑 Borrar
        </button>
      </div>

      {/* Finish button */}
      {mode === 'drawing' && vertices.length >= 3 && (
        <button
          onClick={onFinish}
          style={{
            width: '100%', background: '#166534', color: '#4ade80',
            border: '1px solid #22c55e', borderRadius: '6px', padding: '6px',
            fontSize: '12px', fontWeight: 700, cursor: 'pointer', marginBottom: '6px',
          }}
        >
          ✅ Finalizar polígono
        </button>
      )}

      {/* Status */}
      <div style={{
        borderTop: '1px solid #334155', paddingTop: '6px',
        fontSize: '11px', color: statusColor, lineHeight: 1.4,
      }}>
        {statusMsg}
      </div>
    </div>,
    containerRef.current
  )
}

// ── Map internals ─────────────────────────────────────────────────────────────

const vertexIcon = () => L.divIcon({
  className: '',
  html: `<div style="width:16px;height:16px;border-radius:50%;background:#f59e0b;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,.6);cursor:grab"></div>`,
  iconSize: [16, 16], iconAnchor: [8, 8],
})

function CursorStyle({ mode }: { mode: Mode }) {
  const map = useMap()
  useEffect(() => {
    map.getContainer().style.cursor = mode === 'drawing' ? 'crosshair' : ''
  }, [mode, map])
  return null
}

function ClickToAdd({ active, onAdd }: { active: boolean; onAdd: (p: LatLng) => void }) {
  useMapEvents({
    click(e) { if (active) onAdd([e.latlng.lat, e.latlng.lng]) },
    dblclick(e) { if (active) e.originalEvent.preventDefault() },
  })
  return null
}

function RubberBand({ active, vertices }: { active: boolean; vertices: LatLng[] }) {
  const map = useMap()
  const line = useRef<L.Polyline | null>(null)
  useEffect(() => {
    const rm = () => { line.current?.remove(); line.current = null }
    if (!active || !vertices.length) { rm(); return }
    const fn = (e: L.LeafletMouseEvent) => {
      const pts: L.LatLngExpression[] = [vertices[vertices.length - 1], [e.latlng.lat, e.latlng.lng]]
      if (!line.current) line.current = L.polyline(pts, { color: '#3b82f6', weight: 2, dashArray: '6 4', opacity: .9 }).addTo(map)
      else line.current.setLatLngs(pts)
    }
    map.on('mousemove', fn)
    return () => { map.off('mousemove', fn); rm() }
  }, [active, vertices, map])
  return null
}

function ZoomToFit({ vertices, sensors }: { vertices: LatLng[]; sensors: MapAnimal[] }) {
  const map = useMap()
  const done = useRef(false)
  useEffect(() => {
    if (done.current) return
    if (vertices.length >= 2) {
      map.fitBounds(L.latLngBounds(vertices), { padding: [50, 50], maxZoom: 17 })
      done.current = true
      return
    }
    if (sensors.length > 0) {
      const points = sensors.map(s => [s.lat, s.lon] as LatLng)
      map.fitBounds(L.latLngBounds(points), { padding: [70, 70], maxZoom: 17 })
      done.current = true
    }
  }, [vertices, sensors, map])
  return null
}

const sensorIcon = (sensor: MapAnimal) => L.divIcon({
  className: '',
  html: `<div style="width:24px;height:24px;border-radius:999px;background:${sensor.outside_field ? '#ef4444' : '#22c55e'};border:3px solid white;box-shadow:0 2px 10px rgba(0,0,0,.55);display:grid;place-items:center;color:white;font-size:12px;font-weight:800">${sensor.outside_field ? '!' : ''}</div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12],
})

function DragVertex({ pos, index, onDrag, onDelete }: {
  pos: LatLng; index: number
  onDrag: (i: number, p: LatLng) => void
  onDelete: (i: number) => void
}) {
  return (
    <Marker position={pos} draggable icon={vertexIcon()}
      eventHandlers={{
        dragend(e) { const ll = e.target.getLatLng(); onDrag(index, [ll.lat, ll.lng]) },
        contextmenu() { onDelete(index) },
      }}
    />
  )
}

// ── Main ─────────────────────────────────────────────────────────────────────

interface Props {
  vertices: LatLng[]
  onVerticesChange: (v: LatLng[]) => void
  otherPaddocks?: Paddock[]
  sensors?: MapAnimal[]
  center?: LatLng
  mapHeight?: number
  color?: string
}

export default function PaddockMapEditor({
  vertices, onVerticesChange, otherPaddocks = [], sensors = [], center, mapHeight = 440, color: selectedColor = '#22c55e',
}: Props) {
  const [mode, setMode] = useState<Mode>('idle')

  useEffect(() => { if (vertices.length === 0) setMode('idle') }, [vertices.length])

  const add = useCallback((p: LatLng) => onVerticesChange([...vertices, p]), [vertices, onVerticesChange])
  const drag = useCallback((i: number, p: LatLng) => {
    const n = [...vertices]; n[i] = p; onVerticesChange(n)
  }, [vertices, onVerticesChange])
  const del = useCallback((i: number) => {
    const n = vertices.filter((_, j) => j !== i)
    onVerticesChange(n)
    if (n.length < 3) setMode('idle')
  }, [vertices, onVerticesChange])

  const area = calcAreaHa(vertices)
  const color = mode === 'editing' ? '#f59e0b' : mode === 'drawing' ? '#3b82f6' : selectedColor

  const mapCenter: LatLng = center ?? (vertices.length > 0
    ? [vertices.reduce((s, [y]) => s + y, 0) / vertices.length, vertices.reduce((s, [, x]) => s + x, 0) / vertices.length]
    : [-31.70, -60.80])

  return (
    <div style={{ width: '100%', height: `${mapHeight}px`, borderRadius: '10px', overflow: 'hidden', border: '1px solid #334155' }}>
      <MapContainer center={mapCenter} zoom={15} style={{ height: '100%', width: '100%' }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" attribution="&copy; OpenStreetMap" />

        <CursorStyle mode={mode} />
        <ClickToAdd active={mode === 'drawing'} onAdd={add} />
        <RubberBand active={mode === 'drawing'} vertices={vertices} />
        <ZoomToFit vertices={vertices} sensors={sensors} />

        {/* Toolbar — rendered as a Leaflet control via portal */}
        <ToolbarControl
          mode={mode} vertices={vertices} area={area}
          onDraw={() => mode === 'drawing' ? setMode('idle') : setMode('drawing')}
          onEdit={() => mode === 'editing' ? setMode('idle') : setMode('editing')}
          onUndo={() => onVerticesChange(vertices.slice(0, -1))}
          onClear={() => { onVerticesChange([]); setMode('idle') }}
          onFinish={() => setMode('idle')}
        />

        {otherPaddocks.map(p => {
          const verts = geoJsonToLeaflet(p.polygon)
          return verts.length >= 3 ? (
            <Polygon key={p.id} positions={verts}
              pathOptions={{ color: p.color || '#475569', fillColor: p.color || '#475569', fillOpacity: .12, weight: 1.5, dashArray: '4 3' }} />
          ) : null
        })}

        {vertices.length >= 3 &&
          <Polygon positions={vertices}
            pathOptions={{ color, fillColor: color, fillOpacity: .2, weight: 2.5 }} />
        }

        {sensors.map(sensor => (
          <Marker key={sensor.device_id} position={[sensor.lat, sensor.lon]} icon={sensorIcon(sensor)}>
          </Marker>
        ))}

        {mode === 'drawing' && vertices.map((v, i) =>
          <CircleMarker key={i} center={v} radius={7}
            pathOptions={{ color: '#3b82f6', fillColor: 'white', fillOpacity: 1, weight: 2.5 }} />
        )}

        {mode === 'editing' && vertices.map((v, i) =>
          <DragVertex key={i} pos={v} index={i} onDrag={drag} onDelete={del} />
        )}

        {mode === 'idle' && vertices.length >= 3 && vertices.map((v, i) =>
          <CircleMarker key={i} center={v} radius={4}
            pathOptions={{ color: '#22c55e', fillColor: 'white', fillOpacity: 1, weight: 2 }} />
        )}
      </MapContainer>
    </div>
  )
}
