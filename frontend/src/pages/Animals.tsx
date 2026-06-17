import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Search, Edit2, MapPin, Save, X, Battery, Thermometer, AlertCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { Animal, LoraDevice } from '@/types'
import { cn } from '@/lib/utils'
import Header from '@/components/layout/Header'

interface DeviceRow {
  dev_addr: string
  name: string | null
  device_type: string
  battery_pct: number | null
  temperature: number | null
  online: number
  last_seen: string | null
  lat: number | null
  lon: number | null
  animal: Animal | null
}

function batteryColor(bat: number | null) {
  if (bat == null) return '#94a3b8'
  if (bat <= 20) return '#ef4444'
  if (bat <= 50) return '#f59e0b'
  return '#22c55e'
}

export default function Animals() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [editingAddr, setEditingAddr] = useState<string | null>(null)
  const [editName, setEditName] = useState('')

  const { data: devices = [] } = useQuery<LoraDevice[]>({
    queryKey: ['animals-devices'],
    queryFn: () => api.get('/lora/devices').then(r => r.data.devices),
    refetchInterval: 15_000,
  })

  const { data: animals = [] } = useQuery<Animal[]>({
    queryKey: ['animals-list'],
    queryFn: () => api.get('/animals?page_size=200').then(r => r.data.items),
  })

  const updateDevice = useMutation({
    mutationFn: (data: { dev_addr: string; name: string }) =>
      api.put(`/lora/devices/${encodeURIComponent(data.dev_addr)}`, data),
    onSuccess: () => {
      toast.success('Nombre actualizado')
      setEditingAddr(null)
      qc.invalidateQueries({ queryKey: ['animals-devices'] })
    },
    onError: () => toast.error('Error al actualizar'),
  })

  const startEdit = (d: LoraDevice) => {
    setEditingAddr(d.dev_addr)
    setEditName(d.name || '')
  }

  const saveEdit = (devAddr: string) => {
    updateDevice.mutate({ dev_addr: devAddr, name: editName })
  }

  // Merge LoRa devices with PostgreSQL animals
  const rows: DeviceRow[] = devices.map(d => {
    const animal = animals.find(a => a.device_uid === d.dev_addr || a.device_uid === d.name)
    return {
      dev_addr: d.dev_addr,
      name: d.name,
      device_type: d.device_type,
      battery_pct: d.battery_pct,
      temperature: d.temperature,
      online: d.online,
      last_seen: d.last_seen,
      lat: d.lat,
      lon: d.lon,
      animal: animal || null,
    }
  })

  const filtered = search
    ? rows.filter(r =>
        r.dev_addr.toLowerCase().includes(search.toLowerCase()) ||
        (r.name || '').toLowerCase().includes(search.toLowerCase()) ||
        (r.animal?.ear_tag || '').toLowerCase().includes(search.toLowerCase())
      )
    : rows

  const handleGpsClick = (devAddr: string) => {
    navigate(`/map?highlight=${encodeURIComponent(devAddr)}`)
  }

  return (
    <div className="flex flex-col h-full">
      <Header title="Animales" subtitle={`${rows.length} collares · ${rows.filter(r => r.online >= 1).length} online`} />

      <div className="flex-1 overflow-auto p-4 sm:p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="relative flex-1 max-w-sm">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text" placeholder="Buscar collar o caravana..." value={search}
              onChange={e => setSearch(e.target.value)} className="input pl-9"
            />
          </div>
        </div>

        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-700 text-left">
                  <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase">Collar</th>
                  <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase">Animal</th>
                  <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase">Estado</th>
                  <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase">Bat</th>
                  <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase">Temp</th>
                  <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase">GPS</th>
                  <th className="px-3 py-2.5 text-xs font-semibold text-slate-400 uppercase">Última</th>
                  <th className="px-3 py-2.5 w-20"></th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr><td colSpan={8} className="px-3 py-12 text-center text-slate-500">
                    {devices.length === 0 ? 'No hay collares registrados' : 'Sin resultados'}
                  </td></tr>
                ) : filtered.map(row => {
                  const isEditing = editingAddr === row.dev_addr
                  const hasAnimal = row.animal != null
                  const hasGps = row.lat != null && row.lon != null
                  return (
                    <tr key={row.dev_addr} className={cn('table-row', isEditing && 'bg-surface-800/50')}>
                      <td className="px-3 py-2.5">
                        {isEditing ? (
                          <div className="flex items-center gap-1">
                            <input value={editName} onChange={e => setEditName(e.target.value)}
                              className="bg-surface-700 border border-surface-600 rounded px-2 py-1 text-xs text-white w-28 focus:outline-none focus:border-brand-500" />
                            <button onClick={() => saveEdit(row.dev_addr)} className="text-emerald-400 p-1"><Save size={12} /></button>
                            <button onClick={() => setEditingAddr(null)} className="text-slate-400 p-1"><X size={12} /></button>
                          </div>
                        ) : (
                          <div>
                            <span className="text-white font-mono text-xs">{row.name || row.dev_addr}</span>
                            <span className="text-[10px] text-slate-500 block">{row.device_type}</span>
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2.5">
                        {hasAnimal ? (
                          <div>
                            <span className="text-slate-200 font-medium">{row.animal!.ear_tag}</span>
                            {row.animal!.name && <span className="text-slate-400 text-xs ml-1">({row.animal!.name})</span>}
                            <span className="text-[10px] text-slate-500 block">{row.animal!.breed || 'Sin raza'} · {row.animal!.sex === 'female' ? 'Hembra' : 'Macho'}</span>
                          </div>
                        ) : (
                          <span className="text-amber-500 text-xs flex items-center gap-1">
                            <AlertCircle size={11} /> Falta completar
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5">
                        <span className={cn('inline-flex items-center gap-1.5 text-xs', row.online >= 1 ? 'text-emerald-400' : 'text-red-400')}>
                          <span className={cn('w-1.5 h-1.5 rounded-full', row.online >= 1 ? 'bg-emerald-400 animate-pulse' : 'bg-red-400')} />
                          {row.online >= 1 ? 'Online' : 'Offline'}
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="flex items-center gap-1 text-xs tabular-nums">
                          <Battery size={11} style={{ color: batteryColor(row.battery_pct) }} />
                          <span style={{ color: batteryColor(row.battery_pct) }} className="font-semibold">
                            {row.battery_pct != null ? Math.round(row.battery_pct) + '%' : '—'}
                          </span>
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="flex items-center gap-1 text-xs tabular-nums">
                          <Thermometer size={11} className={row.temperature != null && row.temperature > 35 ? 'text-red-400' : 'text-slate-400'} />
                          <span className={row.temperature != null && row.temperature > 35 ? 'text-red-400' : 'text-slate-300'}>
                            {row.temperature != null ? row.temperature.toFixed(1) + '°C' : '—'}
                          </span>
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        <button
                          onClick={() => handleGpsClick(row.dev_addr)}
                          className={cn('flex items-center gap-1 text-xs transition-colors', hasGps ? 'text-emerald-400 hover:text-emerald-300' : 'text-slate-500 hover:text-slate-400')}
                          title={hasGps ? 'Ver en mapa' : 'Sin GPS'}
                        >
                          <MapPin size={12} className={hasGps ? 'animate-pulse' : ''} />
                          {hasGps ? 'Ver' : '—'}
                        </button>
                      </td>
                      <td className="px-3 py-2.5 text-slate-400 text-[11px] whitespace-nowrap">
                        {row.last_seen
                          ? new Date(row.last_seen).toLocaleString('es-AR', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })
                          : '—'}
                      </td>
                      <td className="px-3 py-2.5">
                        {!isEditing && (
                          <button onClick={() => startEdit(row.dev_addr as any)} className="p-1 text-slate-500 hover:text-brand-400">
                            <Edit2 size={13} />
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
