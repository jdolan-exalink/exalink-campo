import { useQuery } from '@tanstack/react-query'
import { Syringe } from 'lucide-react'
import api from '@/lib/api'
import { formatDate } from '@/lib/utils'
import Header from '@/components/layout/Header'

interface HealthEventLocal {
  id: string
  animal_id: string
  event_type: string
  product_name: string
  dose: string | null
  event_date: string
  next_date: string | null
  vet_name: string | null
  created_at: string
}

export default function Health() {
  const { data: events = [], isLoading } = useQuery<HealthEventLocal[]>({
    queryKey: ['health'],
    queryFn: () => api.get('/health?limit=100').then(r => r.data),
  })

  const EVENT_LABELS: Record<string, string> = {
    vaccine: 'Vacuna', treatment: 'Tratamiento', disease: 'Enfermedad',
    surgery: 'Cirugía', checkup: 'Revisión', deworming: 'Desparasitación', vitamin: 'Vitamina'
  }

  return (
    <div className="flex flex-col h-full">
      <Header title="Sanidad" subtitle="Historial de eventos sanitarios" />
      <div className="flex-1 overflow-auto p-6">
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-700">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Animal</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Tipo</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Producto</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Dosis</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Fecha</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Próxima</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Veterinario</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 6 }).map((_, i) => (
                  <tr key={i} className="border-b border-surface-700">
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j} className="px-4 py-3"><div className="h-4 bg-surface-700 rounded animate-pulse" /></td>
                    ))}
                  </tr>
                ))
              ) : events.map((ev) => (
                <tr key={ev.id} className="table-row">
                  <td className="px-4 py-3 font-mono text-xs text-slate-300">{ev.animal_id.slice(0, 8)}...</td>
                  <td className="px-4 py-3">
                    <span className="badge text-xs bg-brand-400/10 text-brand-400 border-brand-400/20">
                      {EVENT_LABELS[ev.event_type] || ev.event_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-200">{ev.product_name}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{ev.dose || '—'}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{formatDate(ev.event_date)}</td>
                  <td className="px-4 py-3 text-xs">
                    {ev.next_date ? (
                      <span className={new Date(ev.next_date) < new Date() ? 'text-warning' : 'text-slate-400'}>
                        {formatDate(ev.next_date)}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{ev.vet_name || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
