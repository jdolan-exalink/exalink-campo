import { useState } from 'react'
import { Heart, X } from 'lucide-react'
import { db, type LocalAnimal, type LocalRepro, type ReproTipo } from '@/lib/db'
import toast from 'react-hot-toast'
import { cn } from '@/lib/utils'

interface Props {
  animal: LocalAnimal
  onClose: () => void
  onSaved: () => void
}

const TIPOS: { value: ReproTipo; label: string }[] = [
  { value: 'heat',             label: 'Celo detectado' },
  { value: 'service',          label: 'Servicio natural' },
  { value: 'insemination',     label: 'Inseminación artificial' },
  { value: 'pregnancy_check',  label: 'Diagnóstico preñez' },
  { value: 'birth',            label: 'Parto' },
  { value: 'abortion',         label: 'Aborto / Pérdida' },
  { value: 'drying',           label: 'Secado' },
]

export default function ReproModal({ animal, onClose, onSaved }: Props) {
  const [tipo, setTipo] = useState<ReproTipo>('service')
  const [fecha, setFecha] = useState(new Date().toISOString().slice(0, 10))
  const [obs, setObs] = useState('')
  const [saving, setSaving] = useState(false)

  const save = async () => {
    setSaving(true)
    try {
      const repro: LocalRepro = {
        id: crypto.randomUUID(),
        animal_id: animal.id,
        server_animal_id: animal.server_id,
        tipo,
        fecha,
        observaciones: obs.trim() || undefined,
        sync_status: 'pending',
        created_at: new Date().toISOString(),
      }

      await db.reproducciones.add(repro)

      const label = TIPOS.find(t => t.value === tipo)?.label ?? tipo
      toast.success(`Evento registrado: ${label}`)
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
            <Heart size={18} className="text-pink-400" />
            <div>
              <p className="text-white font-semibold text-sm">Evento Reproductivo</p>
              <p className="text-slate-400 text-xs">{animal.ear_tag}{animal.name ? ` · ${animal.name}` : ''}</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-surface-800">
            <X size={16} />
          </button>
        </div>

        <div className="space-y-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Tipo de evento *</label>
            <div className="grid grid-cols-1 gap-1.5">
              {TIPOS.map(t => (
                <button
                  key={t.value}
                  onClick={() => setTipo(t.value)}
                  className={cn(
                    'px-3 py-2 rounded-lg text-sm text-left font-medium transition-colors',
                    tipo === t.value
                      ? 'bg-pink-600/30 border border-pink-500/50 text-pink-300'
                      : 'bg-surface-800 border border-transparent text-slate-300 hover:bg-surface-700'
                  )}
                >
                  {t.label}
                </button>
              ))}
            </div>
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
            disabled={saving}
            className={cn(
              'flex-1 px-4 py-2.5 rounded-lg text-sm font-semibold transition-colors',
              saving
                ? 'bg-pink-700/50 text-pink-400/50 cursor-not-allowed'
                : 'bg-pink-600 hover:bg-pink-500 text-white'
            )}
          >
            {saving ? 'Guardando...' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  )
}
