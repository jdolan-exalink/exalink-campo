import { useState, useEffect, useRef } from 'react'
import {
  Bluetooth, BluetoothOff, Search, Scale, Heart,
  CheckCircle, AlertCircle, ChevronRight, Wifi, WifiOff, Tag
} from 'lucide-react'
import { db, type LocalAnimal } from '@/lib/db'
import { cn } from '@/lib/utils'
import {
  isBluetoothAvailable,
  connectRFIDReader,
  disconnectRFIDReader,
  getConnectedDeviceName,
  type BTStatus,
} from '@/lib/bluetooth'
import WeightModal from './WeightModal'
import ReproModal from './ReproModal'
import toast from 'react-hot-toast'

const CATEGORIA_LABEL: Record<string, string> = {
  ternero: 'Ternero', ternera: 'Ternera', novillo: 'Novillo',
  vaquillona: 'Vaquillona', toro: 'Toro', vaca: 'Vaca', buey: 'Buey',
}

const SYNC_COLOR: Record<string, string> = {
  synced: 'text-emerald-400',
  pending: 'text-amber-400',
  conflict: 'text-red-400',
}

const SYNC_LABEL: Record<string, string> = {
  synced: 'Sincronizado',
  pending: 'Pendiente',
  conflict: 'Conflicto',
}

export default function MangaTab() {
  const [btStatus, setBtStatus] = useState<BTStatus>('disconnected')
  const [connectedDevice, setConnectedDevice] = useState<string | null>(null)
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<LocalAnimal[]>([])
  const [selectedAnimal, setSelectedAnimal] = useState<LocalAnimal | null>(null)
  const [modal, setModal] = useState<'weight' | 'repro' | null>(null)
  const [lastScan, setLastScan] = useState<string | null>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  useEffect(() => {
    const on = () => setIsOnline(true)
    const off = () => setIsOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off) }
  }, [])

  // RFID scan handler
  const handleRFID = async (rfid: string) => {
    setLastScan(rfid)
    const results = await db.animals.where('rfid').equals(rfid).toArray()
    if (results.length === 1) {
      setSelectedAnimal(results[0])
      setQuery(results[0].ear_tag)
      setSearchResults([])
      toast.success(`Escaneado: ${results[0].ear_tag}`, { icon: '📡' })
    } else if (results.length === 0) {
      toast.error(`RFID no encontrado localmente: ${rfid}`)
    } else {
      setSearchResults(results)
    }
  }

  const connectBT = async () => {
    try {
      await connectRFIDReader(handleRFID, (status) => {
        setBtStatus(status)
        if (status === 'connected') {
          setConnectedDevice(getConnectedDeviceName())
        } else if (status === 'disconnected') {
          setConnectedDevice(null)
        }
      })
    } catch (e: any) {
      if (e?.name !== 'NotFoundError') {  // user cancelled device picker
        toast.error('Error al conectar lector RFID')
      }
    }
  }

  const disconnectBT = async () => {
    await disconnectRFIDReader()
    setConnectedDevice(null)
  }

  // Manual search
  useEffect(() => {
    if (!query.trim()) {
      setSearchResults([])
      return
    }
    const q = query.trim().toLowerCase()
    const timer = setTimeout(async () => {
      const results = await db.animals
        .filter(a =>
          a.ear_tag.toLowerCase().includes(q) ||
          (a.name ?? '').toLowerCase().includes(q) ||
          (a.rfid ?? '').toLowerCase().includes(q)
        )
        .limit(10)
        .toArray()
      setSearchResults(results)
    }, 150)
    return () => clearTimeout(timer)
  }, [query])

  const selectAnimal = (a: LocalAnimal) => {
    setSelectedAnimal(a)
    setQuery(a.ear_tag)
    setSearchResults([])
    searchRef.current?.blur()
  }

  const clearSelection = () => {
    setSelectedAnimal(null)
    setQuery('')
    setSearchResults([])
    searchRef.current?.focus()
  }

  const afterModal = async () => {
    setModal(null)
    // Refresh local animal in case weight_kg was updated
    if (selectedAnimal) {
      const refreshed = await db.animals.get(selectedAnimal.id)
      if (refreshed) setSelectedAnimal(refreshed)
    }
  }

  return (
    <div className="p-4 space-y-4 max-w-lg mx-auto">
      {/* Connection status bar */}
      <div className="flex items-center justify-between">
        <div className={cn('flex items-center gap-1.5 text-xs', isOnline ? 'text-emerald-400' : 'text-slate-500')}>
          {isOnline ? <Wifi size={12} /> : <WifiOff size={12} />}
          {isOnline ? 'En línea' : 'Offline — datos locales'}
        </div>

        {isBluetoothAvailable() && (
          <button
            onClick={btStatus === 'connected' ? disconnectBT : connectBT}
            disabled={btStatus === 'connecting'}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors',
              btStatus === 'connected'
                ? 'bg-emerald-900/50 text-emerald-300 border border-emerald-700'
                : btStatus === 'connecting'
                ? 'bg-amber-900/50 text-amber-300 border border-amber-700 cursor-wait'
                : 'bg-surface-800 text-slate-300 border border-surface-700 hover:bg-surface-700'
            )}
          >
            {btStatus === 'connected'
              ? <><Bluetooth size={11} /> {connectedDevice ?? 'RFID conectado'}</>
              : btStatus === 'connecting'
              ? <><Bluetooth size={11} /> Conectando...</>
              : <><BluetoothOff size={11} /> Conectar lector RFID</>
            }
          </button>
        )}
      </div>

      {/* Last RFID scan indicator */}
      {lastScan && btStatus === 'connected' && (
        <div className="flex items-center gap-2 px-3 py-2 bg-surface-800 rounded-lg border border-surface-700 text-xs">
          <Tag size={12} className="text-brand-400 shrink-0" />
          <span className="text-slate-400">Último escaneo:</span>
          <span className="text-white font-mono">{lastScan}</span>
        </div>
      )}

      {/* Search input */}
      {!selectedAnimal && (
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            ref={searchRef}
            type="text"
            placeholder="Buscar por caravana, nombre o RFID..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="input w-full pl-10 text-base py-3"
            autoComplete="off"
          />
          {/* Search results dropdown */}
          {searchResults.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-surface-800 border border-surface-600 rounded-xl overflow-hidden shadow-xl">
              {searchResults.map(a => (
                <button
                  key={a.id}
                  onClick={() => selectAnimal(a)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-surface-700 text-left transition-colors"
                >
                  <div className="flex-1">
                    <span className="text-white font-semibold">{a.ear_tag}</span>
                    {a.name && <span className="text-slate-400 text-sm ml-1.5">{a.name}</span>}
                    <div className="text-xs text-slate-500 mt-0.5">
                      {CATEGORIA_LABEL[a.category ?? ''] ?? a.category ?? '—'} · {a.sex === 'female' ? 'Hembra' : 'Macho'}
                    </div>
                  </div>
                  <div className={cn('text-xs', SYNC_COLOR[a.sync_status])}>
                    {SYNC_LABEL[a.sync_status]}
                  </div>
                  <ChevronRight size={14} className="text-slate-600" />
                </button>
              ))}
            </div>
          )}
          {query.trim() && searchResults.length === 0 && (
            <div className="absolute z-10 w-full mt-1 bg-surface-800 border border-surface-600 rounded-xl px-4 py-4 text-center shadow-xl">
              <AlertCircle size={16} className="text-slate-500 mx-auto mb-1" />
              <p className="text-sm text-slate-400">Sin resultados locales</p>
              <p className="text-xs text-slate-600 mt-0.5">Sincronice para descargar animales</p>
            </div>
          )}
        </div>
      )}

      {/* Animal card */}
      {selectedAnimal && (
        <div className="space-y-3">
          <div className="bg-surface-800 border border-surface-700 rounded-2xl p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold text-white">{selectedAnimal.ear_tag}</span>
                  {selectedAnimal.rfid && (
                    <span className="text-xs font-mono bg-surface-700 text-brand-300 px-2 py-0.5 rounded">
                      RFID
                    </span>
                  )}
                </div>
                {selectedAnimal.name && (
                  <p className="text-slate-300 font-medium mt-0.5">{selectedAnimal.name}</p>
                )}
              </div>
              <div className="flex flex-col items-end gap-1">
                <span className={cn('text-xs font-medium', SYNC_COLOR[selectedAnimal.sync_status])}>
                  {SYNC_LABEL[selectedAnimal.sync_status]}
                </span>
                <button onClick={clearSelection} className="text-xs text-slate-500 hover:text-slate-300 underline">
                  Cambiar
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="bg-surface-900 rounded-lg px-3 py-2">
                <p className="text-xs text-slate-500 mb-0.5">Categoría</p>
                <p className="text-white font-medium">{CATEGORIA_LABEL[selectedAnimal.category ?? ''] ?? '—'}</p>
              </div>
              <div className="bg-surface-900 rounded-lg px-3 py-2">
                <p className="text-xs text-slate-500 mb-0.5">Sexo</p>
                <p className="text-white font-medium">{selectedAnimal.sex === 'female' ? 'Hembra' : 'Macho'}</p>
              </div>
              {selectedAnimal.breed && (
                <div className="bg-surface-900 rounded-lg px-3 py-2">
                  <p className="text-xs text-slate-500 mb-0.5">Raza</p>
                  <p className="text-white font-medium">{selectedAnimal.breed}</p>
                </div>
              )}
              {selectedAnimal.weight_kg != null && (
                <div className="bg-surface-900 rounded-lg px-3 py-2">
                  <p className="text-xs text-slate-500 mb-0.5">Peso</p>
                  <p className="text-white font-medium">{selectedAnimal.weight_kg} kg</p>
                </div>
              )}
            </div>

            {selectedAnimal.notes && (
              <p className="mt-2 text-xs text-slate-400 italic">{selectedAnimal.notes}</p>
            )}
          </div>

          {/* Action buttons */}
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setModal('weight')}
              className="flex flex-col items-center gap-2 py-4 bg-brand-600/20 border border-brand-600/40 rounded-xl text-brand-300 hover:bg-brand-600/30 transition-colors"
            >
              <Scale size={22} />
              <span className="text-sm font-semibold">Pesaje</span>
            </button>
            <button
              onClick={() => setModal('repro')}
              className="flex flex-col items-center gap-2 py-4 bg-pink-600/20 border border-pink-600/40 rounded-xl text-pink-300 hover:bg-pink-600/30 transition-colors"
            >
              <Heart size={22} />
              <span className="text-sm font-semibold">Reproducción</span>
            </button>
          </div>

          {/* Next animal quick button */}
          <button
            onClick={clearSelection}
            className="w-full flex items-center justify-center gap-2 py-3 bg-surface-800 border border-surface-700 rounded-xl text-slate-300 hover:bg-surface-700 text-sm font-medium transition-colors"
          >
            <CheckCircle size={16} className="text-emerald-400" />
            Siguiente animal
          </button>
        </div>
      )}

      {/* Empty state */}
      {!selectedAnimal && !query && (
        <div className="text-center py-10 text-slate-500">
          <Search size={32} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">Busque un animal por caravana o RFID</p>
          {btStatus !== 'connected' && isBluetoothAvailable() && (
            <p className="text-xs mt-1 text-slate-600">También puede conectar un lector RFID Bluetooth</p>
          )}
        </div>
      )}

      {/* Modals */}
      {modal === 'weight' && selectedAnimal && (
        <WeightModal animal={selectedAnimal} onClose={() => setModal(null)} onSaved={afterModal} />
      )}
      {modal === 'repro' && selectedAnimal && (
        <ReproModal animal={selectedAnimal} onClose={() => setModal(null)} onSaved={afterModal} />
      )}
    </div>
  )
}
