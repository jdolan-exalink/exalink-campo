import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { X, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { Paddock, Establishment } from '@/types'
import PaddockMapEditor, {
  type LatLng,
  geoJsonToLeaflet,
  leafletToGeoJson,
  calcAreaHa,
} from '@/components/map/PaddockMapEditor'

const schema = z.object({
  name: z.string().min(1, 'El nombre es obligatorio'),
  code: z.string().optional(),
  color: z.string().regex(/^#[0-9a-fA-F]{6}$/).default('#22c55e'),
  area_ha: z.coerce.number().positive().optional().or(z.literal('')),
  max_capacity: z.coerce.number().int().positive().optional().or(z.literal('')),
  pasture_type: z.string().optional(),
  water_source: z.boolean().default(true),
  status: z.enum(['empty', 'occupied', 'resting', 'maintenance']).default('empty'),
  notes: z.string().optional(),
})
type FormValues = z.infer<typeof schema>

interface Props {
  isOpen: boolean
  onClose: () => void
  paddock?: Paddock | null
}

export default function PaddockFormModal({ isOpen, onClose, paddock }: Props) {
  const qc = useQueryClient()
  const [vertices, setVertices] = useState<LatLng[]>([])

  const { data: establishments = [] } = useQuery<Establishment[]>({
    queryKey: ['establishments'],
    queryFn: () => api.get('/establishments').then(r => r.data),
    enabled: isOpen,
  })

  const { data: allPaddocks = [] } = useQuery<Paddock[]>({
    queryKey: ['paddocks'],
    queryFn: () => api.get('/paddocks').then(r => r.data),
    enabled: isOpen,
  })

  const { register, handleSubmit, reset, watch, setValue, formState: { errors } } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  useEffect(() => {
    if (!isOpen) return
    if (paddock) {
      reset({
        name: paddock.name,
        code: paddock.code ?? '',
        color: paddock.color ?? '#22c55e',
        area_ha: paddock.area_ha ?? '',
        max_capacity: paddock.max_capacity ?? '',
        pasture_type: paddock.pasture_type ?? '',
        water_source: true,
        status: paddock.status,
        notes: paddock.notes ?? '',
      })
      setVertices(geoJsonToLeaflet(paddock.polygon))
    } else {
      reset({ water_source: true, status: 'empty', color: '#22c55e' })
      setVertices([])
    }
  }, [isOpen, paddock?.id]) // eslint-disable-line

  const saveMutation = useMutation({
    mutationFn: async (data: FormValues) => {
      const estId = establishments[0]?.id
      if (!estId) throw new Error('No hay establecimientos registrados')
      const payload = {
        name: data.name,
        code: data.code || null,
        color: data.color || '#22c55e',
        area_ha: data.area_ha || null,
        max_capacity: data.max_capacity || null,
        pasture_type: data.pasture_type || null,
        water_source: data.water_source,
        status: data.status,
        notes: data.notes || null,
        polygon: leafletToGeoJson(vertices),
        ...(paddock ? {} : { establishment_id: estId }),
      }
      return paddock
        ? api.put(`/paddocks/${paddock.id}`, payload)
        : api.post('/paddocks', payload)
    },
    onSuccess: () => {
      toast.success(paddock ? 'Potrero actualizado' : 'Potrero creado')
      qc.invalidateQueries({ queryKey: ['paddocks'] })
      qc.invalidateQueries({ queryKey: ['map-data'] })
      qc.invalidateQueries({ queryKey: ['map-data-real-lora'] })
      qc.invalidateQueries({ queryKey: ['kpis'] })
      onClose()
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Error al guardar'),
  })

  if (!isOpen) return null

  const otherPaddocks = allPaddocks.filter(p => p.id !== paddock?.id)
  const estCenter: LatLng | undefined =
    establishments[0]?.lat != null
      ? [establishments[0].lat!, establishments[0].lon!]
      : undefined
  const area = calcAreaHa(vertices)
  const selectedColor = watch('color') || paddock?.color || '#22c55e'

  return (
    /* ── Overlay ── */
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: 'rgba(0,0,0,0.7)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '16px',
      }}
      onClick={onClose}
    >
      {/* ── Modal box ── */}
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#0f172a',
          border: '1px solid #334155',
          borderRadius: '16px',
          boxShadow: '0 25px 60px rgba(0,0,0,0.8)',
          width: '100%',
          maxWidth: '1100px',
          maxHeight: '92vh',
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '16px 24px',
          borderBottom: '1px solid #334155',
          flexShrink: 0,
        }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#f1f5f9' }}>
              {paddock ? `Editar: ${paddock.name}` : 'Nuevo potrero'}
            </h2>
            <p style={{ margin: '4px 0 0', fontSize: '12px', color: '#94a3b8' }}>
              Completá los campos y dibujá el límite en el mapa
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: '#64748b', padding: '6px', borderRadius: '8px',
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body — grid layout: form left, map right */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '260px 1fr',
          gap: '0',
          flex: 1,
        }}>
          {/* ── Form column ── */}
          <div style={{
            borderRight: '1px solid #334155',
            padding: '20px',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}>
            <Field label="Nombre *" error={errors.name?.message}>
              <input {...register('name')} className="input" placeholder="Potrero A1" autoFocus />
            </Field>

            <Field label="Código">
              <input {...register('code')} className="input" placeholder="A1" />
            </Field>

            <Field label="Color">
              <input type="hidden" {...register('color')} />
              <div style={{ display: 'grid', gridTemplateColumns: '40px 1fr', gap: '8px', alignItems: 'center' }}>
                <input
                  type="color"
                  value={selectedColor}
                  onChange={e => setValue('color', e.target.value, { shouldDirty: true, shouldValidate: true })}
                  style={{ width: '40px', height: '36px', padding: '2px', borderRadius: '8px', border: '1px solid #334155', background: '#0f172a' }}
                />
                <select
                  value={selectedColor}
                  onChange={e => setValue('color', e.target.value, { shouldDirty: true, shouldValidate: true })}
                  className="input"
                >
                  <option value="#22c55e">Verde</option>
                  <option value="#3b82f6">Azul</option>
                  <option value="#f59e0b">Amarillo</option>
                  <option value="#ef4444">Rojo</option>
                  <option value="#a855f7">Violeta</option>
                  <option value="#14b8a6">Turquesa</option>
                  <option value="#64748b">Gris</option>
                </select>
              </div>
            </Field>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <Field label={`Área (ha)${area > 0 ? ` · ${area.toFixed(1)}` : ''}`} error={errors.area_ha?.message}>
                <input type="number" step="0.1" min="0" {...register('area_ha')} className="input" placeholder="45.0" />
              </Field>
              <Field label="Cap. máx.">
                <input type="number" min="0" {...register('max_capacity')} className="input" placeholder="20" />
              </Field>
            </div>

            <Field label="Estado">
              <select {...register('status')} className="input">
                <option value="empty">Vacío</option>
                <option value="occupied">Ocupado</option>
                <option value="resting">Descanso</option>
                <option value="maintenance">Mantenimiento</option>
              </select>
            </Field>

            <Field label="Tipo de pastura">
              <input {...register('pasture_type')} className="input" placeholder="Raigrás, Sorgo..." />
            </Field>

            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input type="checkbox" {...register('water_source')} style={{ width: '16px', height: '16px', accentColor: '#3b82f6' }} />
              <span style={{ fontSize: '13px', color: '#cbd5e1' }}>Fuente de agua</span>
            </label>

            <Field label="Notas">
              <textarea {...register('notes')} className="input" style={{ resize: 'none' }} rows={3} placeholder="Observaciones..." />
            </Field>

            {/* Polygon summary */}
            <div style={{
              padding: '12px', borderRadius: '8px',
              background: vertices.length >= 3 ? 'rgba(34,197,94,0.05)' : '#1e293b',
              border: `1px solid ${vertices.length >= 3 ? 'rgba(34,197,94,0.25)' : '#334155'}`,
            }}>
              <p style={{ margin: '0 0 4px', fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Polígono</p>
              {vertices.length >= 3 ? (
                <p style={{ margin: 0, fontSize: '12px', color: '#4ade80' }}>
                  ✓ {vertices.length} vértices · ~{area.toFixed(1)} ha
                </p>
              ) : (
                <p style={{ margin: 0, fontSize: '12px', color: '#64748b' }}>
                  Sin polígono — usá los botones del mapa para dibujar
                </p>
              )}
            </div>
          </div>

          {/* ── Map column ── */}
          <div style={{ padding: '16px' }}>
            <PaddockMapEditor
              key={paddock?.id ?? 'new-paddock'}
              vertices={vertices}
              onVerticesChange={setVertices}
              otherPaddocks={otherPaddocks}
              center={estCenter}
              color={selectedColor}
              mapHeight={440}
            />
          </div>
        </div>

        {/* Footer */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 24px',
          borderTop: '1px solid #334155',
          flexShrink: 0,
        }}>
          <p style={{ margin: 0, fontSize: '12px', color: '#64748b' }}>
            {vertices.length >= 3
              ? `Polígono con ${vertices.length} vértices · ~${area.toFixed(1)} ha`
              : 'Podés guardar sin polígono'}
          </p>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleSubmit(d => saveMutation.mutate(d))}
              disabled={saveMutation.isPending}
              className="btn-primary"
            >
              {saveMutation.isPending && <Loader2 size={14} className="animate-spin" />}
              {paddock ? 'Guardar cambios' : 'Crear potrero'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, error, children }: {
  label: string; error?: string; children: React.ReactNode
}) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: '11px', fontWeight: 500, color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {label}
      </label>
      {children}
      {error && <p style={{ margin: '4px 0 0', fontSize: '11px', color: '#f87171' }}>{error}</p>}
    </div>
  )
}
