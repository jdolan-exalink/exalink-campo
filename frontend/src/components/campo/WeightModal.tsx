import { useState } from 'react'
import { Scale, X } from 'lucide-react'
import { db, type LocalAnimal, type LocalPesaje } from '@/lib/db'
import toast from 'react-hot-toast'
import { cn } from '@/lib/utils'

interface Props {
  animal: LocalAnimal
  onClose: () => void
  onSaved: () => void
}

const METODOS = ['Báscula manga', 'Báscula corral', 'Estimado visual', 'Cinta métrica']

export default function WeightModal({ animal, onClose, onSaved }: Props) {
  const [peso, setPeso] = useState('')
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10))
  const [metodo, setMetodo] = useState(METODOS[0])
  const [obs, setObs] = useState('')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    const kg = parseFloat(peso)
    if (isNaN(kg) || kg <= 0 || kg > 2000) {
      toast.error('Peso inválido')
      return
    }

    setSaving(true)
    try {
      const pesaje: LocalPesaje = {
        id: crypto.randomUUID(),
        animal_id: animal.id,
        server_animal_id: animal.server_id,
        peso_kg: kg,
        fecha,
        metodo,
        observaciones: obs.trim() || undefined,
        sync_status: 'pending',
        created_at: new Date().toISOString(),
      }

      await db.pesajes.add(pesaje)

      // Update animal's local weight_kg (optimistic)
      await db.animals.update(animal.id, {
        weight_kg: kg,
        sync_status: animal.sync_status === 'synced' ? 'pending' : animal.sync_status,
        updated_at_local: new Date().toISOString(),
      })

      toast.success(`Pesaje registrado: ${kg} kg`)
      onSaved()
    } catch (e) {
      toast.error('Error al guardar')
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-surface-900 border border-surface-700 rounded-t-2xl sm:rounded-2xl w-full sm:max-w-sm p-5 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Scale size={18} className="text-brand-400" />
            <div>
              <p className="text-white font-semibold text-sm">Registrar Pesaje</p>
              <p className="text-slate-400 text-xs">{animal.ear_tag}{animal.name ? ` · ${animal.name}` : ''}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-surface-800">
            <X size={16} />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Peso (kg) *</label>
            <input
              type="number"
              step="0.5"
              min="1"
              max="2000"
              placeholder="Ej: 320"
              value={peso}
              onChange={e => setPeso(e.target.value)}
              className="input w-full text-lg font-semibold"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Fecha</label>
            <input
              type="date"
              value={fecha}
              onChange={e => setFecha(e.target.value)}
              className="input w-full"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Método</label>
            <select
              value={metodo}
              onChange={e => setMetodo(e.target.value)}
              className="input w-full"
            >
              {METODOS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1">Observaciones</label>
            <textarea
              value={obs}
              onChange={e => setObs(e.target.value)}
              className="input w-full h-16 resize-none text-sm"
              placeholder="Opcional..."
            />
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2.5 rounded-lg bg-surface-800 text-slate-300 hover:bg-surface-700 text-sm font-medium transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={save}
            disabled={!peso || saving}
            className={cn(
              'flex-1 px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors',
              !peso || saving
                ? 'bg-brand-700/50 text-brand-400/50 cursor-not-allowed'
                : 'bg-brand-600 hover:bg-brand-500 text-white'
            )}
          >
            {saving ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  )
}
