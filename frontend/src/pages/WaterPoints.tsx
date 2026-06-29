import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Droplets, Plus, Edit2, Trash2, MapPin, Clock, Activity } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { WaterPoint, ZoneVisit, Establishment } from '@/types'
import Header from '@/components/layout/Header'
import WaterPointFormModal from '@/components/waterpoints/WaterPointFormModal'

const TYPE_LABEL: Record<string, string> = { water: 'Aguada', trough: 'Bebedero' }
const TYPE_STYLE: Record<string, string> = {
  water: 'text-sky-400 bg-sky-400/10 border-sky-400/20',
  trough: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20',
}

const EVENT_LABEL: Record<string, string> = {
  paddock_enter: 'Entró a corral',
  paddock_exit: 'Salió de corral',
  water_visit: 'Visita a agua',
}
const EVENT_STYLE: Record<string, string> = {
  paddock_enter: 'text-field bg-field/10 border-field/20',
  paddock_exit: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  water_visit: 'text-sky-400 bg-sky-400/10 border-sky-400/20',
}

const fmtDuration = (s: number | null) => {
  if (s == null) return '—'
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.round(s / 60)} min`
  return `${(s / 3600).toFixed(1)} h`
}

const fmtTime = (iso: string) =>
  new Date(iso).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

export default function WaterPoints() {
  const qc = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<WaterPoint | null>(null)
  const [selectedWpId, setSelectedWpId] = useState<string | null>(null)

  const { data: establishments = [] } = useQuery<Establishment[]>({
    queryKey: ['establishments'],
    queryFn: () => api.get('/establishments').then(r => r.data),
  })
  const estId = establishments[0]?.id ?? null

  const { data: waterPoints = [], isLoading } = useQuery<WaterPoint[]>({
    queryKey: ['water-points'],
    queryFn: () => api.get('/water-points').then(r => r.data),
  })

  const { data: visits = [] } = useQuery<ZoneVisit[]>({
    queryKey: ['zone-visits', selectedWpId],
    queryFn: () => {
      if (selectedWpId) return api.get(`/water-points/${selectedWpId}/visits?limit=50`).then(r => r.data)
      return api.get('/zone-visits?limit=50').then(r => r.data)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/water-points/${id}`),
    onSuccess: () => {
      toast.success('Punto de agua eliminado')
      qc.invalidateQueries({ queryKey: ['water-points'] })
      qc.invalidateQueries({ queryKey: ['water-points-map'] })
    },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Error al eliminar'),
  })

  const openCreate = () => { setEditing(null); setModalOpen(true) }
  const openEdit = (wp: WaterPoint) => { setEditing(wp); setModalOpen(true) }
  const closeModal = () => { setModalOpen(false); setEditing(null) }

  const activeWp = waterPoints.find(w => w.id === selectedWpId) || null

  return (
    <>
      <div className="flex flex-col h-full">
        <Header title="Puntos de agua" subtitle={`${waterPoints.length} puntos · ${waterPoints.filter(w => w.is_active).length} activos`} />

        <div className="flex-1 overflow-auto page-pad">
          <div className="flex items-center justify-between gap-3 mb-4 sm:mb-6">
            <div className="flex items-center gap-2 min-w-0 text-xs sm:text-sm text-slate-400 truncate">
              <Droplets size={15} className="text-sky-400 flex-shrink-0" />
              Trazabilidad de visitas a agua y movimientos entre corrales
            </div>
            <button onClick={openCreate} className="btn-primary flex-shrink-0">
              <Plus size={15} /> Nuevo
            </button>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 sm:gap-4">
              {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-40 bg-surface-800 rounded-xl animate-pulse" />)}
            </div>
          ) : waterPoints.length === 0 ? (
            <div className="card p-8 sm:p-12 text-center">
              <Droplets size={40} className="text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400 mb-4">No hay puntos de agua registrados</p>
              <button onClick={openCreate} className="btn-primary"><Plus size={14} /> Crear primer punto</button>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
              {/* Listado de water points */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 content-start">
                {waterPoints.map(wp => (
                  <div
                    key={wp.id}
                    className={`card p-4 transition-all group cursor-pointer ${selectedWpId === wp.id ? 'border-sky-400/60' : 'hover:border-surface-600'}`}
                    onClick={() => setSelectedWpId(selectedWpId === wp.id ? null : wp.id)}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-start gap-3 min-w-0">
                        <div className="mt-0.5 w-8 h-8 rounded-lg bg-sky-400/10 border border-sky-400/20 flex items-center justify-center flex-shrink-0">
                          <Droplets size={15} className="text-sky-400" />
                        </div>
                        <div className="min-w-0">
                          <h3 className="font-semibold text-white truncate">{wp.name}</h3>
                          <p className="text-xs text-slate-500 font-mono mt-0.5 flex items-center gap-1">
                            <MapPin size={10} /> {wp.lat.toFixed(5)}, {wp.lon.toFixed(5)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <span className={`badge text-[10px] ${TYPE_STYLE[wp.type] ?? TYPE_STYLE.water}`}>{TYPE_LABEL[wp.type] ?? wp.type}</span>
                        {!wp.is_active && <span className="badge text-[10px] text-slate-500 bg-slate-500/10 border-slate-500/20">Inactivo</span>}
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="text-center p-2 bg-surface-900 rounded-lg">
                        <p className="text-sm font-bold text-sky-300 tabular-nums">{wp.radius_m} m</p>
                        <p className="text-[10px] text-slate-500">Radio</p>
                      </div>
                      <div className="text-center p-2 bg-surface-900 rounded-lg">
                        <p className="text-sm font-bold text-white tabular-nums">{wp.capacity_l ?? '—'}</p>
                        <p className="text-[10px] text-slate-500">Litros</p>
                      </div>
                      <div className="text-center p-2 bg-surface-900 rounded-lg">
                        <p className="text-sm font-bold text-white tabular-nums">
                          {visits.filter(v => v.water_point_id === wp.id).length}
                        </p>
                        <p className="text-[10px] text-slate-500">Visitas</p>
                      </div>
                    </div>

                    <div className="mt-3 flex items-center justify-end gap-1">
                      <button
                        onClick={(e) => { e.stopPropagation(); openEdit(wp) }}
                        className="p-1.5 text-slate-400 hover:text-sky-400 hover:bg-sky-400/10 rounded transition-all lg:opacity-0 lg:group-hover:opacity-100"
                        title="Editar"
                      >
                        <Edit2 size={13} />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); confirm(`Eliminar ${wp.name}?`) && deleteMutation.mutate(wp.id) }}
                        className="p-1.5 text-slate-400 hover:text-danger hover:bg-danger/10 rounded transition-all lg:opacity-0 lg:group-hover:opacity-100"
                        title="Eliminar"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Panel de visitas recientes */}
              <aside className="card p-4 lg:sticky lg:top-4 self-start">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Activity size={15} className="text-sky-400" />
                    {activeWp ? `Visitas — ${activeWp.name}` : 'Visitas recientes'}
                  </h3>
                  {selectedWpId && (
                    <button onClick={() => setSelectedWpId(null)} className="text-[11px] text-slate-400 hover:text-white">Ver todas</button>
                  )}
                </div>

                {visits.length === 0 ? (
                  <p className="text-sm text-slate-500 text-center py-8">
                    Sin visitas registradas todavía.
                    <br />
                    <span className="text-xs">Aparecerán cuando los sensores pasen por los puntos.</span>
                  </p>
                ) : (
                  <div className="space-y-2 max-h-[60vh] overflow-y-auto">
                    {visits.map(v => (
                      <div key={v.id} className="rounded-lg border border-surface-700 bg-surface-800 p-3 text-xs">
                        <div className="flex items-center justify-between gap-2 mb-1.5">
                          <span className={`badge text-[10px] ${EVENT_STYLE[v.event_type] ?? ''}`}>
                            {EVENT_LABEL[v.event_type] ?? v.event_type}
                          </span>
                          <span className="text-slate-500 flex items-center gap-1">
                            <Clock size={10} /> {fmtDuration(v.duration_s)}
                          </span>
                        </div>
                        <p className="text-slate-300 font-medium truncate">
                          {v.water_point_name || v.paddock_name || v.dev_addr}
                        </p>
                        <p className="text-slate-500 mt-0.5">
                          {v.dev_addr} · {fmtTime(v.entered_at)}
                          {v.exited_at ? ` → ${fmtTime(v.exited_at)}` : ' (en curso)'}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </aside>
            </div>
          )}
        </div>
      </div>

      <WaterPointFormModal
        isOpen={modalOpen}
        onClose={closeModal}
        waterPoint={editing}
        establishmentId={estId}
      />
    </>
  )
}
