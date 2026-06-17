import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, AlertCircle, Info, CheckCircle2 } from 'lucide-react'
import api from '@/lib/api'
import type { Alert } from '@/types'
import { alertTypeLabel, timeAgo, severityColor, cn } from '@/lib/utils'

const SeverityIcon = ({ severity }: { severity: string }) => {
  if (severity === 'critical') return <AlertCircle size={14} className="text-danger flex-shrink-0" />
  if (severity === 'warning') return <AlertTriangle size={14} className="text-warning flex-shrink-0" />
  return <Info size={14} className="text-blue-400 flex-shrink-0" />
}

export default function AlertsFeed() {
  const { data: alerts = [], isLoading } = useQuery<Alert[]>({
    queryKey: ['alerts-feed'],
    queryFn: () => api.get('/alerts?status=open&limit=20').then(r => r.data),
    refetchInterval: 15_000,
  })

  return (
    <div className="card flex flex-col h-full">
      <div className="p-4 border-b border-surface-700 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Alertas Activas</h3>
        <span className="badge bg-danger/10 text-danger border-danger/20 text-xs">
          {alerts.filter(a => a.severity === 'critical').length} críticas
        </span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-12 bg-surface-700 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : alerts.length === 0 ? (
          <div className="p-8 text-center">
            <CheckCircle2 size={32} className="text-field mx-auto mb-2" />
            <p className="text-sm text-slate-400">Sin alertas activas</p>
          </div>
        ) : (
          <div className="divide-y divide-surface-700">
            {alerts.map((alert) => (
              <div key={alert.id} className="p-3 hover:bg-surface-700/50 transition-colors">
                <div className="flex items-start gap-2.5">
                  <SeverityIcon severity={alert.severity} />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-slate-200 truncate">{alert.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={cn('badge text-[10px]', severityColor[alert.severity as keyof typeof severityColor])}>
                        {alertTypeLabel[alert.alert_type] || alert.alert_type}
                      </span>
                      <span className="text-[10px] text-slate-500">{timeAgo(alert.created_at)}</span>
                    </div>
                    {alert.animal_ear_tag && (
                      <p className="text-[10px] text-slate-500 mt-0.5">Caravana: {alert.animal_ear_tag}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
