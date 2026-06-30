import { useMemo, useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Settings2, ThermometerSun, ThermometerSnowflake, BatteryLow, WifiOff, TimerOff, MapPinOff, Fence, Loader2, RefreshCw, Bell } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { AlertConfig, AlertType, AlertSeverity } from '@/types'
import { cn } from '@/lib/utils'
import Header from '@/components/layout/Header'
import Switch from '@/components/ui/Switch'

interface ConfigMeta {
  icon: typeof ThermometerSun
  desc: string
  threshold: 'min' | 'max' | 'value' | null
  thresholdUnit?: string
  thresholdPlaceholder?: string
}

const CONFIG_META: Record<AlertType, ConfigMeta> = {
  temperature_low: {
    icon: ThermometerSnowflake,
    desc: 'Dispara cuando la temperatura reportada baja del umbral.',
    threshold: 'min',
    thresholdUnit: '°C',
    thresholdPlaceholder: '0',
  },
  temperature_high: {
    icon: ThermometerSun,
    desc: 'Dispara cuando la temperatura reportada supera el umbral.',
    threshold: 'max',
    thresholdUnit: '°C',
    thresholdPlaceholder: '40',
  },
  low_battery: {
    icon: BatteryLow,
    desc: 'Dispara cuando la batería del dispositivo cae por debajo del %.',
    threshold: 'value',
    thresholdUnit: '%',
    thresholdPlaceholder: '20',
  },
  device_offline: {
    icon: WifiOff,
    desc: 'Dispara cuando un dispositivo deja de transmitir.',
    threshold: null,
  },
  prolonged_disconnect: {
    icon: TimerOff,
    desc: 'Dispara cuando un dispositivo lleva desconectado más de X minutos.',
    threshold: 'value',
    thresholdUnit: 'min',
    thresholdPlaceholder: '60',
  },
  outside_geofence: {
    icon: Fence,
    desc: 'Dispara cuando un animal sale de la geocerca configurada.',
    threshold: null,
  },
  outside_field: {
    icon: MapPinOff,
    desc: 'Dispara cuando un animal sale del campo establecido.',
    threshold: null,
  },
  // No configurables por ahora (se listan sólo si llegan del backend)
  immobile: { icon: WifiOff, desc: '', threshold: null },
  abnormal_activity: { icon: WifiOff, desc: '', threshold: null },
  possible_heat: { icon: WifiOff, desc: '', threshold: null },
  possible_birth: { icon: WifiOff, desc: '', threshold: null },
  vaccine_due: { icon: WifiOff, desc: '', threshold: null },
  manual: { icon: WifiOff, desc: '', threshold: null },
}

const ORDER: AlertType[] = [
  'temperature_low', 'temperature_high', 'low_battery', 'device_offline',
  'prolonged_disconnect', 'outside_geofence', 'outside_field',
]

const SEVERITY_OPTIONS: { value: AlertSeverity; label: string }[] = [
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Advertencia' },
  { value: 'critical', label: 'Crítica' },
]

export default function AlertConfigPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [notifPerm, setNotifPerm] = useState<NotificationPermission>(
    typeof Notification !== 'undefined' ? Notification.permission : 'denied'
  )

  useEffect(() => {
    if (typeof Notification === 'undefined') return
    const onChange = () => setNotifPerm(Notification.permission)
    onChange()
    // Algunos navegadores no disparan evento; sondeamos al montar
    return () => {}
  }, [])

  const requestNotifPermission = async () => {
    if (typeof Notification === 'undefined') {
      toast.error('Tu navegador no soporta notificaciones')
      return
    }
    try {
      const res = await Notification.requestPermission()
      setNotifPerm(res)
      if (res === 'granted') {
        toast.success('Notificaciones activadas')
        new Notification('Notificaciones de ExaLink Campo activadas', { body: 'Recibirás alertas en el navegador.' })
      } else {
        toast('Permiso de notificaciones denegado', { icon: '🔕' })
      }
    } catch {
      toast.error('No se pudo solicitar el permiso')
    }
  }

  const { data: configs = [], isLoading } = useQuery<AlertConfig[]>({
    queryKey: ['alert-configs'],
    queryFn: () => api.get('/alert-configs').then(r => r.data),
  })

  const seedMutation = useMutation({
    mutationFn: () => api.post('/alert-configs/seed-defaults'),
    onSuccess: () => { toast.success('Configuraciones por defecto restauradas'); qc.invalidateQueries({ queryKey: ['alert-configs'] }) },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<AlertConfig> }) =>
      api.put(`/alert-configs/${id}`, patch),
    onMutate: async ({ id, patch }) => {
      await qc.cancelQueries({ queryKey: ['alert-configs'] })
      const prev = qc.getQueryData<AlertConfig[]>(['alert-configs'])
      qc.setQueryData<AlertConfig[]>(['alert-configs'], (old = []) =>
        old.map(c => (c.id === id ? { ...c, ...patch } : c))
      )
      return { prev }
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(['alert-configs'], ctx.prev)
      toast.error('Error al guardar')
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alert-configs'] }),
  })

  const ordered = useMemo(() => {
    const byType = new Map(configs.map(c => [c.alert_type, c]))
    return ORDER.map(t => byType.get(t)).filter(Boolean) as AlertConfig[]
  }, [configs])

  const enabledCount = ordered.filter(c => c.enabled).length

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Configuración de alertas"
        subtitle={`${enabledCount}/${ordered.length} reglas activas`}
        actions={
          <button
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
            className="btn-secondary text-xs"
            title="Restaurar configuraciones por defecto"
          >
            {seedMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            <span className="hidden sm:inline">Restaurar defaults</span>
          </button>
        }
      />

      <div className="flex-1 overflow-auto p-4 sm:p-6 max-w-4xl mx-auto w-full">
        <button
          onClick={() => navigate('/alerts')}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 mb-4"
        >
          <ArrowLeft size={14} /> Volver a alertas
        </button>

        <div className="flex items-start gap-3 mb-6 p-4 rounded-xl bg-surface-800/50 border border-surface-700">
          <Settings2 size={18} className="text-brand-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-slate-400 leading-relaxed flex-1">
            Configurá qué alertas querés recibir, sus umbrales, cada cuánto repetirlas y si emitir
            notificaciones del navegador. Las alertas desactivadas no se generan.
          </div>
        </div>

        <div className={cn(
          'flex items-center gap-3 mb-4 p-3 rounded-xl border text-xs',
          notifPerm === 'granted'
            ? 'bg-field/5 border-field/20 text-slate-400'
            : 'bg-warning/5 border-warning/20 text-slate-300'
        )}>
          <Bell size={16} className={notifPerm === 'granted' ? 'text-field' : 'text-warning'} />
          <span className="flex-1">
            {notifPerm === 'granted'
              ? 'Notificaciones del navegador activadas.'
              : 'Activá las notificaciones del navegador para recibir avisos de alertas.'}
          </span>
          {notifPerm !== 'granted' && (
            <button onClick={requestNotifPermission} className="btn-secondary text-xs py-1.5 px-3">
              Activar
            </button>
          )}
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-28 bg-surface-800 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {ordered.map(cfg => (
              <ConfigCard
                key={cfg.id}
                cfg={cfg}
                onPatch={(patch) => updateMutation.mutate({ id: cfg.id, patch })}
                saving={updateMutation.isPending}
              />
            ))}
            {ordered.length === 0 && (
              <div className="card p-12 text-center">
                <Settings2 size={36} className="text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400 mb-4">Sin configuraciones todavía</p>
                <button onClick={() => seedMutation.mutate()} className="btn-primary">
                  Crear configuraciones por defecto
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function ConfigCard({
  cfg,
  onPatch,
  saving,
}: {
  cfg: AlertConfig
  onPatch: (patch: Partial<AlertConfig>) => void
  saving: boolean
}) {
  const meta = CONFIG_META[cfg.alert_type]
  const Icon = meta.icon
  const dim = cfg.enabled ? '' : 'opacity-60'

  return (
    <div className={cn('card p-4 transition-opacity', dim)}>
      <div className="flex items-start gap-3">
        <div className={cn(
          'w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0',
          cfg.enabled ? 'bg-brand-600/15 text-brand-400' : 'bg-surface-700 text-slate-500'
        )}>
          <Icon size={17} />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white truncate">{cfg.name || cfg.alert_type}</p>
              <p className="text-xs text-slate-500 mt-0.5">{meta.desc}</p>
            </div>
            <Switch checked={cfg.enabled} onChange={(v) => onPatch({ enabled: v })} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
            {/* Umbral */}
            <Field label="Umbral">
              {meta.threshold === null ? (
                <div className="input py-1.5 text-slate-500 text-xs flex items-center h-[34px]">—</div>
              ) : meta.threshold === 'min' ? (
                <div className="flex items-center">
                  <span className="text-slate-500 text-xs mr-1">≤</span>
                  <input
                    type="number"
                    value={cfg.threshold_min ?? ''}
                    onChange={e => onPatch({ threshold_min: e.target.value === '' ? null : Number(e.target.value) })}
                    placeholder={meta.thresholdPlaceholder}
                    className="input py-1.5 text-xs"
                    disabled={!cfg.enabled}
                  />
                  {meta.thresholdUnit && <span className="text-slate-500 text-xs ml-1">{meta.thresholdUnit}</span>}
                </div>
              ) : meta.threshold === 'max' ? (
                <div className="flex items-center">
                  <span className="text-slate-500 text-xs mr-1">≥</span>
                  <input
                    type="number"
                    value={cfg.threshold_max ?? ''}
                    onChange={e => onPatch({ threshold_max: e.target.value === '' ? null : Number(e.target.value) })}
                    placeholder={meta.thresholdPlaceholder}
                    className="input py-1.5 text-xs"
                    disabled={!cfg.enabled}
                  />
                  {meta.thresholdUnit && <span className="text-slate-500 text-xs ml-1">{meta.thresholdUnit}</span>}
                </div>
              ) : (
                <div className="flex items-center">
                  <input
                    type="number"
                    value={cfg.threshold_value ?? ''}
                    onChange={e => onPatch({ threshold_value: e.target.value === '' ? null : Number(e.target.value) })}
                    placeholder={meta.thresholdPlaceholder}
                    className="input py-1.5 text-xs"
                    disabled={!cfg.enabled}
                  />
                  {meta.thresholdUnit && <span className="text-slate-500 text-xs ml-1">{meta.thresholdUnit}</span>}
                </div>
              )}
            </Field>

            {/* Severidad */}
            <Field label="Severidad">
              <select
                value={cfg.severity}
                onChange={e => onPatch({ severity: e.target.value as AlertSeverity })}
                className="input py-1.5 text-xs"
                disabled={!cfg.enabled}
              >
                {SEVERITY_OPTIONS.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </Field>

            {/* Repetición */}
            <Field label="Repetir cada">
              <div className="flex items-center">
                <input
                  type="number"
                  min={0}
                  value={cfg.repeat_interval_minutes}
                  onChange={e => onPatch({ repeat_interval_minutes: Number(e.target.value) })}
                  className="input py-1.5 text-xs"
                  disabled={!cfg.enabled}
                />
                <span className="text-slate-500 text-xs ml-1">min</span>
              </div>
            </Field>

            {/* Notif browser */}
            <Field label="Notif. browser">
              <div className="h-[34px] flex items-center">
                <Switch
                  checked={cfg.browser_notify}
                  onChange={(v) => onPatch({ browser_notify: v })}
                  size="sm"
                  color="sky"
                />
              </div>
            </Field>
          </div>
        </div>

        {saving && <Loader2 size={14} className="animate-spin text-slate-500 flex-shrink-0 mt-1" />}
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[10px] font-medium uppercase tracking-wide text-slate-500 mb-1">{label}</label>
      {children}
    </div>
  )
}
