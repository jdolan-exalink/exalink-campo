import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layers, Users, Ruler, Cpu, Plus, Edit2 } from 'lucide-react'
import api from '@/lib/api'
import type { Paddock } from '@/types'
import { cn } from '@/lib/utils'
import Header from '@/components/layout/Header'
import PaddockFormModal from '@/components/paddocks/PaddockFormModal'

const STATUS_STYLES: Record<string, string> = {
  occupied: 'text-field bg-field/10 border-field/20',
  empty: 'text-slate-400 bg-slate-400/10 border-slate-400/20',
  resting: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
  maintenance: 'text-warning bg-warning/10 border-warning/20',
}
const STATUS_LABEL: Record<string, string> = {
  occupied: 'Ocupado', empty: 'Vacío', resting: 'Descanso', maintenance: 'Mantenimiento',
}

export default function Paddocks() {
  const [modalOpen, setModalOpen] = useState(false)
  const [editingPaddock, setEditingPaddock] = useState<Paddock | null>(null)

  const { data: paddocks = [], isLoading } = useQuery<Paddock[]>({
    queryKey: ['paddocks'],
    queryFn: () => api.get('/paddocks').then(r => r.data),
  })

  const openCreate = () => {
    setEditingPaddock(null)
    setModalOpen(true)
  }

  const openEdit = (paddock: Paddock) => {
    setEditingPaddock(paddock)
    setModalOpen(true)
  }

  const closeModal = () => {
    setModalOpen(false)
    setEditingPaddock(null)
  }

  return (
    <>
      <div className="flex flex-col h-full">
        <Header title="Potreros" subtitle={`${paddocks.length} potreros registrados`} />

        <div className="flex-1 overflow-auto p-6">
          {/* Toolbar */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-400">
                {paddocks.filter(p => p.status === 'occupied').length} ocupados ·{' '}
                {paddocks.filter(p => p.status === 'empty').length} vacíos
              </span>
            </div>
            <button onClick={openCreate} className="btn-primary">
              <Plus size={15} /> Nuevo potrero
            </button>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-44 bg-surface-800 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : paddocks.length === 0 ? (
            <div className="card p-12 text-center">
              <Layers size={40} className="text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400 mb-4">No hay potreros aún</p>
              <button onClick={openCreate} className="btn-primary">
                <Plus size={14} /> Crear primer potrero
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {paddocks.map((p) => (
                <div
                  key={p.id}
                  className="card p-5 hover:border-surface-600 transition-all group"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-start gap-3">
                      <span
                        className="mt-1 h-4 w-4 rounded border border-white/60 shadow-sm shrink-0"
                        style={{ backgroundColor: p.color || '#22c55e' }}
                      />
                      <div>
                        <h3 className="font-semibold text-white">{p.name}</h3>
                        {p.code && (
                          <p className="text-xs text-slate-500 font-mono mt-0.5">{p.code}</p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={cn('badge text-xs', STATUS_STYLES[p.status] ?? STATUS_STYLES.empty)}>
                        {STATUS_LABEL[p.status] ?? p.status}
                      </span>
                      <button
                        onClick={() => openEdit(p)}
                        className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-brand-400 hover:bg-brand-400/10 rounded transition-all"
                        title="Editar potrero"
                      >
                        <Edit2 size={13} />
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
                    <div className="text-center p-2 bg-surface-900 rounded-lg">
                      <Users size={13} className="text-slate-500 mx-auto mb-1" />
                      <p className="text-base font-bold text-white tabular-nums">
                        {p.current_load}
                        {p.max_capacity ? `/${p.max_capacity}` : ''}
                      </p>
                      <p className="text-[10px] text-slate-500">Animales</p>
                    </div>
                    <div className="text-center p-2 bg-surface-900 rounded-lg">
                      <Cpu size={13} className="text-slate-500 mx-auto mb-1" />
                      <p className="text-base font-bold text-white tabular-nums">
                        {p.device_count ?? '—'}
                      </p>
                      <p className="text-[10px] text-slate-500">Collares</p>
                    </div>
                    <div className="text-center p-2 bg-surface-900 rounded-lg">
                      <Ruler size={13} className="text-slate-500 mx-auto mb-1" />
                      <p className="text-base font-bold text-white tabular-nums">
                        {p.area_ha ? p.area_ha.toFixed(1) : '—'}
                      </p>
                      <p className="text-[10px] text-slate-500">Hectáreas</p>
                    </div>
                    <div className="text-center p-2 bg-surface-900 rounded-lg">
                      <Layers size={13} className="text-slate-500 mx-auto mb-1" />
                      <p className="text-base font-bold text-white tabular-nums">
                        {p.area_ha && p.current_load > 0
                          ? (p.current_load / p.area_ha).toFixed(2)
                          : '—'}
                      </p>
                      <p className="text-[10px] text-slate-500">Cab/ha</p>
                    </div>
                  </div>

                  {p.pasture_type && (
                    <p className="text-xs text-slate-500 mt-3">Pastura: {p.pasture_type}</p>
                  )}

                  {/* Polygon indicator */}
                  <div className="mt-3 flex items-center justify-between">
                    <span className={cn(
                      'text-xs',
                      p.polygon ? 'text-field' : 'text-slate-600'
                    )}>
                      {p.polygon ? '✓ Polígono definido' : '○ Sin polígono'}
                    </span>
                  </div>

                  {/* Occupancy bar */}
                  {p.max_capacity && p.current_load > 0 && (
                    <div className="mt-2">
                      <div className="h-1.5 bg-surface-700 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-full rounded-full transition-all',
                            p.current_load / p.max_capacity > 0.9 ? 'bg-danger' : 'bg-field'
                          )}
                          style={{
                            width: `${Math.min((p.current_load / p.max_capacity) * 100, 100)}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <PaddockFormModal
        isOpen={modalOpen}
        onClose={closeModal}
        paddock={editingPaddock}
      />
    </>
  )
}
