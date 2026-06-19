import { useState, useEffect } from 'react'
import { Search, AlertCircle, CheckCircle, Clock, Tag } from 'lucide-react'
import { db, type LocalAnimal, type SyncStatus } from '@/lib/db'
import { cn } from '@/lib/utils'

const CATEGORIA_LABEL: Record<string, string> = {
  ternero: 'Ternero', ternera: 'Ternera', novillo: 'Novillo',
  vaquillona: 'Vaquillona', toro: 'Toro', vaca: 'Vaca', buey: 'Buey',
}

const STATUS_CFG: Record<SyncStatus, { icon: typeof CheckCircle; color: string; label: string }> = {
  synced:   { icon: CheckCircle, color: 'text-emerald-400', label: 'Sincronizado' },
  pending:  { icon: Clock,       color: 'text-amber-400',   label: 'Pendiente' },
  conflict: { icon: AlertCircle, color: 'text-red-400',     label: 'Conflicto' },
}

function SyncBadge({ status }: { status: SyncStatus }) {
  const { icon: Icon, color, label } = STATUS_CFG[status]
  return (
    <span className={cn('flex items-center gap-1 text-xs', color)}>
      <Icon size={11} />
      {label}
    </span>
  )
}

export default function AnimalesTab() {
  const [animals, setAnimals] = useState<LocalAnimal[]>([])
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<SyncStatus | 'all'>('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      let all = await db.animals.toArray()
      setAnimals(all)
      setLoading(false)
    }
    load()
  }, [])

  const filtered = animals.filter(a => {
    const matchQuery = !query.trim() ||
      a.ear_tag.toLowerCase().includes(query.toLowerCase()) ||
      (a.name ?? '').toLowerCase().includes(query.toLowerCase()) ||
      (a.rfid ?? '').toLowerCase().includes(query.toLowerCase())
    const matchFilter = filter === 'all' || a.sync_status === filter
    return matchQuery && matchFilter
  })

  const counts = {
    all: animals.length,
    synced: animals.filter(a => a.sync_status === 'synced').length,
    pending: animals.filter(a => a.sync_status === 'pending').length,
    conflict: animals.filter(a => a.sync_status === 'conflict').length,
  }

  return (
    <div className="p-4 space-y-3">
      {/* Search */}
      <div className="relative">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          placeholder="Buscar animal..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="input w-full pl-9"
        />
      </div>

      {/* Filter chips */}
      <div className="flex gap-2 overflow-x-auto pb-0.5">
        {(['all', 'synced', 'pending', 'conflict'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium shrink-0 transition-colors',
              filter === f
                ? 'bg-brand-600 text-white'
                : 'bg-surface-800 text-slate-400 hover:text-slate-200'
            )}
          >
            {f === 'all' ? 'Todos' : f === 'synced' ? 'Sincronizados' : f === 'pending' ? 'Pendientes' : 'Conflictos'}
            <span className={cn(
              'px-1.5 py-0.5 rounded-full text-[10px] leading-none',
              filter === f ? 'bg-white/20 text-white' : 'bg-surface-700 text-slate-400'
            )}>
              {counts[f]}
            </span>
          </button>
        ))}
      </div>

      {/* List */}
      {loading ? (
        <div className="text-center py-12 text-slate-500 text-sm">Cargando...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-slate-500">
          <Search size={28} className="mx-auto mb-2 opacity-40" />
          <p className="text-sm">{animals.length === 0 ? 'No hay animales locales. Sincronice primero.' : 'Sin resultados'}</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {filtered.map(a => (
            <div key={a.id} className="bg-surface-800 border border-surface-700 rounded-xl px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white font-semibold">{a.ear_tag}</span>
                    {a.name && <span className="text-slate-400 text-sm">{a.name}</span>}
                    {a.rfid && (
                      <span className="flex items-center gap-1 text-xs text-brand-400 bg-brand-900/30 px-1.5 py-0.5 rounded">
                        <Tag size={9} />
                        RFID
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5 flex-wrap text-xs text-slate-500">
                    {a.category && <span>{CATEGORIA_LABEL[a.category] ?? a.category}</span>}
                    {a.breed && <><span>·</span><span>{a.breed}</span></>}
                    {a.weight_kg != null && <><span>·</span><span className="text-slate-400 font-medium">{a.weight_kg} kg</span></>}
                  </div>
                </div>
                <SyncBadge status={a.sync_status} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
