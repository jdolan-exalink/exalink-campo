import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import { formatDate } from '@/lib/utils'
import Header from '@/components/layout/Header'

interface WeightRecord {
  id: string
  animal_id: string
  weight_kg: number
  measure_date: string
  method: string | null
  daily_gain: number | null
}

export default function Weights() {
  const { data: records = [], isLoading } = useQuery<WeightRecord[]>({
    queryKey: ['weights'],
    queryFn: () => api.get('/weights?limit=200').then(r => r.data),
  })

  return (
    <div className="flex flex-col h-full">
      <Header title="Pesajes" subtitle="Historial de pesajes" />
      <div className="flex-1 overflow-auto p-6">
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-700">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Animal</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Peso (kg)</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Fecha</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">GDP (kg/día)</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Método</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-surface-700">
                    {Array.from({ length: 5 }).map((_, j) => (
                      <td key={j} className="px-4 py-3"><div className="h-4 bg-surface-700 rounded animate-pulse" /></td>
                    ))}
                  </tr>
                ))
              ) : records.map((r) => (
                <tr key={r.id} className="table-row">
                  <td className="px-4 py-3 font-mono text-xs text-slate-300">{r.animal_id.slice(0, 8)}...</td>
                  <td className="px-4 py-3 text-white font-medium tabular-nums">{r.weight_kg.toFixed(1)}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{formatDate(r.measure_date)}</td>
                  <td className="px-4 py-3 text-xs">
                    {r.daily_gain != null ? (
                      <span className={r.daily_gain >= 0.8 ? 'text-field' : 'text-warning'}>
                        {r.daily_gain.toFixed(3)}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{r.method || 'Manual'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
