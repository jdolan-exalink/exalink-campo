import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, Clock, AlertCircle, AlertTriangle, Info, Settings, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { Alert, AlertStatus, AlertSeverity, AlertType } from '@/types'
import { alertTypeLabel, severityColor, timeAgo, formatDateTime, cn } from '@/lib/utils'
import Header from '@/components/layout/Header'

const SeverityIcon = ({ s }: { s: AlertSeverity }) => {
  if (s === 'critical') return <AlertCircle size={15} className="text-danger flex-shrink-0" />
  if (s === 'warning') return <AlertTriangle size={15} className="text-warning flex-shrink-0" />
  return <Info size={15} className="text-blue-400 flex-shrink-0" />
}

export default function Alerts() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<AlertStatus | ''>('open')
  const [severityFilter, setSeverityFilter] = useState<AlertSeverity | ''>('')
  const [typeFilter, setTypeFilter] = useState<AlertType | ''>('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const { data: alerts = [], isLoading } = useQuery<Alert[]>({
    queryKey: ['alerts', statusFilter, severityFilter, typeFilter, dateFrom, dateTo],
    queryFn: () => {
      const params = new URLSearchParams({ limit: '100' })
      if (statusFilter) params.set('status', statusFilter)
      if (severityFilter) params.set('severity', severityFilter)
      if (typeFilter) params.set('alert_type', typeFilter)
      if (dateFrom) params.set('from', new Date(dateFrom + 'T00:00:00').toISOString())
      if (dateTo) params.set('to', new Date(dateTo + 'T23:59:59').toISOString())
      return api.get(`/alerts?${params}`).then(r => r.data)
    },
    refetchInterval: 20_000,
  })

  const resolveMutation = useMutation({
    mutationFn: (id: string) => api.post(`/alerts/${id}/resolve`),
    onSuccess: () => { toast.success('Alerta resuelta'); qc.invalidateQueries({ queryKey: ['alerts'] }) },
  })

  const ackMutation = useMutation({
    mutationFn: (id: string) => api.post(`/alerts/${id}/acknowledge`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['alerts'] }) },
  })

  const hasDateFilter = dateFrom !== '' || dateTo !== ''
  const clearDateFilter = () => { setDateFrom(''); setDateTo('') }

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Alertas"
        subtitle={`${alerts.length} alertas ${statusFilter || 'totales'}`}
        actions={
          <button
            onClick={() => navigate('/alerts/config')}
            className="btn-secondary text-xs"
            title="Configurar alertas"
          >
            <Settings size={14} /> <span className="hidden sm:inline">Configurar</span>
          </button>
        }
      />

      <div className="flex-1 overflow-auto p-6">
        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <div className="flex rounded-lg bg-surface-800 border border-surface-700 overflow-hidden text-sm">
            {(['open', 'acknowledged', 'resolved', ''] as const).map(s => (
              <button
                key={s || 'all'}
                onClick={() => setStatusFilter(s)}
                className={cn(
                  'px-4 py-2 text-xs font-medium transition-colors',
                  statusFilter === s ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-slate-200'
                )}
              >
                {s === '' ? 'Todas' : s === 'open' ? 'Abiertas' : s === 'acknowledged' ? 'Vistas' : 'Resueltas'}
              </button>
            ))}
          </div>

          <select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value as AlertSeverity | '')}
            className="input w-auto py-1.5"
          >
            <option value="">Toda severidad</option>
            <option value="critical">Crítica</option>
            <option value="warning">Advertencia</option>
            <option value="info">Info</option>
          </select>

          <select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value as AlertType | '')}
            className="input w-auto py-1.5"
          >
            <option value="">Todo tipo</option>
            {(Object.keys(alertTypeLabel) as AlertType[]).map(t => (
              <option key={t} value={t}>{alertTypeLabel[t]}</option>
            ))}
          </select>

          <div className="flex items-center gap-1.5">
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="input w-auto py-1.5"
              title="Desde"
            />
            <span className="text-slate-500 text-xs">→</span>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              className="input w-auto py-1.5"
              title="Hasta"
            />
            {hasDateFilter && (
              <button onClick={clearDateFilter} className="p-1.5 text-slate-400 hover:text-danger rounded" title="Limpiar fechas">
                <X size={14} />
              </button>
            )}
          </div>
        </div>

        <div className="space-y-2">
          {isLoading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-16 bg-surface-800 rounded-xl animate-pulse" />
            ))
          ) : alerts.length === 0 ? (
            <div className="card p-12 text-center">
              <CheckCircle size={40} className="text-field mx-auto mb-3" />
              <p className="text-slate-400">No hay alertas</p>
            </div>
          ) : (
            alerts.map((alert) => (
              <div
                key={alert.id}
                className={cn(
                  'card p-4 flex items-start gap-4 transition-all hover:border-surface-600',
                  alert.severity === 'critical' && alert.status === 'open' && 'border-danger/30'
                )}
              >
                <SeverityIcon s={alert.severity} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-white">{alert.title}</p>
                      {alert.message && <p className="text-xs text-slate-400 mt-0.5">{alert.message}</p>}
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      {alert.status === 'open' && (
                        <>
                          <button
                            onClick={() => ackMutation.mutate(alert.id)}
                            className="btn-secondary text-xs py-1 px-2"
                          >
                            <Clock size={12} /> Ver
                          </button>
                          <button
                            onClick={() => resolveMutation.mutate(alert.id)}
                            className="btn text-xs py-1 px-2 bg-field/10 text-field hover:bg-field/20 border border-field/20"
                          >
                            <CheckCircle size={12} /> Resolver
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 mt-2 flex-wrap">
                    <span className={cn('badge text-xs', severityColor[alert.severity])}>
                      {alertTypeLabel[alert.alert_type]}
                    </span>
                    <span className="text-xs text-slate-500">{formatDateTime(alert.created_at)}</span>
                    {alert.animal_ear_tag && (
                      <span className="text-xs text-slate-500 font-mono">Caravana: {alert.animal_ear_tag}</span>
                    )}
                    {alert.device_uid && (
                      <span className="text-xs text-slate-500 font-mono">{alert.device_uid}</span>
                    )}
                    <span className="text-xs text-slate-600 ml-auto">{timeAgo(alert.created_at)}</span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
