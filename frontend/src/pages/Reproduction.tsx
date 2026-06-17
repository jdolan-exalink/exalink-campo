import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import { formatDate } from '@/lib/utils'
import Header from '@/components/layout/Header'

interface ReproEvent {
  id: string
  animal_id: string
  event_type: string
  event_date: string
  expected_birth_date: string | null
  is_pregnant: boolean | null
  result: string | null
  semen_batch: string | null
  vet_name: string | null
}

const EVENT_LABELS: Record<string, string> = {
  heat: 'Celo', service: 'Servicio', insemination: 'IA',
  pregnancy_check: 'Tacto', birth: 'Parto', abortion: 'Aborto', drying: 'Secado'
}
const EVENT_COLORS: Record<string, string> = {
  heat: 'text-pink-400 bg-pink-400/10 border-pink-400/20',
  service: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
  insemination: 'text-brand-400 bg-brand-400/10 border-brand-400/20',
  pregnancy_check: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
  birth: 'text-field bg-field/10 border-field/20',
  abortion: 'text-danger bg-danger/10 border-danger/20',
  drying: 'text-warning bg-warning/10 border-warning/20',
}

export default function Reproduction() {
  const { data: events = [], isLoading } = useQuery<ReproEvent[]>({
    queryKey: ['reproduction'],
    queryFn: () => api.get('/reproduction?limit=100').then(r => r.data),
  })

  return (
    <div className="flex flex-col h-full">
      <Header title="Reproducción" subtitle="Registro de eventos reproductivos" />
      <div className="flex-1 overflow-auto p-6">
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-700">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Animal</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Evento</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Fecha</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Preñez</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Parto esperado</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Resultado</th>
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
                    <span className={`badge text-xs ${EVENT_COLORS[ev.event_type] || 'text-slate-400 bg-slate-400/10 border-slate-400/20'}`}>
                      {EVENT_LABELS[ev.event_type] || ev.event_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{formatDate(ev.event_date)}</td>
                  <td className="px-4 py-3 text-xs">
                    {ev.is_pregnant === null ? '—' : ev.is_pregnant ? (
                      <span className="text-field">Sí</span>
                    ) : (
                      <span className="text-danger">No</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{formatDate(ev.expected_birth_date)}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{ev.result || '—'}</td>
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
