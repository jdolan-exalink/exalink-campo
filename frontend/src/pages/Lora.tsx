import { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  RadioTower, Activity, Satellite, Database, Clock, Settings, Table, Save,
  Wifi, X, Plus, Trash2, ScrollText, Antenna, Router, Waves, Pencil, Check,
  Battery, BatteryLow, BatteryFull, MapPin, Navigation, KeyRound, RefreshCw
} from 'lucide-react'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { LoraPacketResponse, LoraStats, LoraConfig, LoraPacket, LoraGateway, LoraDevice, LoraPendingGateway } from '@/types'
import { formatDateTime, cn } from '@/lib/utils'
import Header from '@/components/layout/Header'

type Tab = 'reader' | 'gateways' | 'devices' | 'config'

export default function Lora() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = (searchParams.get('tab') as Tab) || 'reader'
  const setTab = (t: Tab) => setSearchParams({ tab: t }, { replace: true })
  const [limit, setLimit] = useState(50)
  const [confirmAction, setConfirmAction] = useState<{ title: string; msg: string; onOk: () => void } | null>(null)
  const [logOpen, setLogOpen] = useState(false)
  const [logLines, setLogLines] = useState<LoraPacket[]>([])
  const logRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()

  const { data: stats, isLoading: statsLoading } = useQuery<LoraStats>({
    queryKey: ['lora-stats'],
    queryFn: () => api.get('/lora/stats').then(r => r.data),
    refetchInterval: 10_000,
  })

  const { data: packetData, isLoading: packetsLoading } = useQuery<LoraPacketResponse>({
    queryKey: ['lora-packets', limit],
    queryFn: () => api.get('/lora/packets', { params: { limit } }).then(r => r.data),
    refetchInterval: 5_000,
  })

  const { data: gateways, isLoading: gwLoading } = useQuery<{ gateways: LoraGateway[] }>({
    queryKey: ['lora-gateways'],
    queryFn: () => api.get('/lora/gateways').then(r => r.data),
    enabled: tab === 'gateways',
  })

  const { data: pending, isLoading: pendingLoading } = useQuery<{ gateways: LoraPendingGateway[] }>({
    queryKey: ['lora-gateways-pending'],
    queryFn: () => api.get('/lora/gateways/pending').then(r => r.data),
    enabled: tab === 'gateways',
    refetchInterval: 15_000,
  })

  const [addGwOpen, setAddGwOpen] = useState(false)

  const { data: devicesData, isLoading: devLoading } = useQuery<{ devices: LoraDevice[] }>({
    queryKey: ['lora-devices'],
    queryFn: () => api.get('/lora/devices').then(r => r.data),
    enabled: tab === 'devices',
  })

  const { data: config, isLoading: configLoading } = useQuery<LoraConfig>({
    queryKey: ['lora-config'],
    queryFn: () => api.get('/lora/config').then(r => r.data),
    enabled: tab === 'config',
  })

  // ── Realtime SSE (always active on this page) ──────────────────
  useEffect(() => {
    const base = api.defaults.baseURL || ''
    const url = `${base}/lora/stream`
    const es = new EventSource(url)
    let lastRefresh = 0
    es.onmessage = (e) => {
      try {
        const pkt = JSON.parse(e.data) as LoraPacket
        if (logOpen) {
          setLogLines(prev => {
            const next = [pkt, ...prev]
            return next.length > 200 ? next.slice(0, 200) : next
          })
        }
        const now = Date.now()
        if (now - lastRefresh > 3000) {
          lastRefresh = now
          queryClient.invalidateQueries({ queryKey: ['lora-stats'] })
          queryClient.invalidateQueries({ queryKey: ['lora-packets'] })
          queryClient.invalidateQueries({ queryKey: ['lora-gateways'] })
          queryClient.invalidateQueries({ queryKey: ['lora-gateways-pending'] })
          queryClient.invalidateQueries({ queryKey: ['lora-devices'] })
        }
      } catch { /* ignore */ }
    }
    es.onerror = () => { es.close() }
    return () => es.close()
  }, [logOpen, queryClient])

  const toggleLog = () => {
    if (logOpen) {
      setLogLines([])
      setLogOpen(false)
    } else {
      setLogOpen(true)
    }
  }

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = 0
  }, [logLines])

  // Auto-scroll: si scrolled arriba, vamos al tope
  const handleLogScroll = () => {
    if (!logRef.current) return
    const el = logRef.current
    if (el.scrollTop === 0) el.scrollTop = 0
  }

  // ── Mutations ─────────────────────────────────────────────────
  const configMutation = useMutation({
    mutationFn: (payload: Partial<LoraConfig>) => api.put('/lora/config', payload),
    onSuccess: () => { toast.success('Configuracion guardada'); queryClient.invalidateQueries({ queryKey: ['lora-config'] }) },
    onError: () => toast.error('Error al guardar'),
  })

  const pairGatewayMutation = useMutation({
    mutationFn: (payload: { gateway_id: string; pairing_code: string; name: string }) =>
      api.post('/lora/gateways/pair', payload),
    onSuccess: (res) => {
      const data = res?.data
      if (data?.ok) {
        toast.success(`Gateway "${data.name}" registrado`)
        setAddGwOpen(false)
      } else {
        toast.error(data?.msg || 'Error al registrar gateway')
      }
      queryClient.invalidateQueries({ queryKey: ['lora-gateways'] })
      queryClient.invalidateQueries({ queryKey: ['lora-gateways-pending'] })
      queryClient.invalidateQueries({ queryKey: ['lora-stats'] })
    },
    onError: (e: any) => toast.error(e?.response?.data?.msg || 'Error al registrar gateway'),
  })

  const deleteGatewayMutation = useMutation({
    mutationFn: (gatewayId: string) => api.delete(`/lora/gateways/${gatewayId}`),
    onSuccess: () => { toast.success('Gateway eliminado'); queryClient.invalidateQueries({ queryKey: ['lora-gateways'] }) },
    onError: () => toast.error('Error al eliminar'),
  })

  const updateGatewayMutation = useMutation({
    mutationFn: (data: { gateway_id: string; name?: string; location?: string; notes?: string }) =>
      api.put(`/lora/gateways/${data.gateway_id}`, { name: data.name, location: data.location, notes: data.notes }),
    onSuccess: () => { toast.success('Gateway actualizado'); queryClient.invalidateQueries({ queryKey: ['lora-gateways'] }) },
    onError: () => toast.error('Error al actualizar'),
  })

  const createDeviceMutation = useMutation({
    mutationFn: (payload: Partial<LoraDevice>) => api.post('/lora/devices', payload),
    onSuccess: () => { toast.success('Dispositivo registrado'); queryClient.invalidateQueries({ queryKey: ['lora-devices'] }) },
    onError: () => toast.error('Error al registrar dispositivo'),
  })

  const deleteDeviceMutation = useMutation({
    mutationFn: (devAddr: string) => api.delete(`/lora/devices/${devAddr}`),
    onSuccess: () => { toast.success('Dispositivo eliminado'); queryClient.invalidateQueries({ queryKey: ['lora-devices'] }) },
    onError: () => toast.error('Error al eliminar'),
  })

  const updateDeviceMutation = useMutation({
    mutationFn: (data: { dev_addr: string; name?: string; device_type?: string; refresh_freq_s?: number }) =>
      api.put(`/lora/devices/${data.dev_addr}`, data),
    onSuccess: () => { toast.success('Dispositivo actualizado'); queryClient.invalidateQueries({ queryKey: ['lora-devices'] }) },
    onError: () => toast.error('Error al actualizar'),
  })

  const clearMutation = useMutation({
    mutationFn: () => api.post('/lora/clear'),
    onSuccess: () => {
      toast.success('Datos limpiados')
      queryClient.invalidateQueries({ queryKey: ['lora-stats'] })
      queryClient.invalidateQueries({ queryKey: ['lora-packets'] })
    },
    onError: () => toast.error('Error al limpiar'),
  })

  const packets = packetData?.packets ?? []
  const total = packetData?.count ?? 0

  return (
    <div className="flex flex-col h-full">
      <Header
        title="LoRaWAN"
        subtitle={`${total} paquetes · ${stats?.unique_gateways ?? 0} gateways · ${stats?.unique_devices ?? 0} dispositivos`}
        actions={
          <div className="flex items-center gap-2">
            <button onClick={toggleLog} className={cn('btn-secondary text-xs flex items-center gap-1.5', logOpen && 'bg-brand-600/20 text-brand-400 border-brand-600')}>
              <ScrollText size={13} />
              {logOpen ? 'Log ON' : 'Log en vivo'}
            </button>
          </div>
        }
      />

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-brand-600/20 flex items-center justify-center"><Database size={16} className="text-brand-400" /></div>
            <div><p className="text-xl font-bold text-white tabular-nums">{statsLoading ? '...' : stats?.total_packets ?? 0}</p><p className="text-xs text-slate-400">Paquetes</p></div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-field/20 flex items-center justify-center"><RadioTower size={16} className="text-field" /></div>
            <div><p className="text-xl font-bold text-white tabular-nums">{statsLoading ? '...' : stats?.unique_gateways ?? 0}</p><p className="text-xs text-slate-400">Gateways activos</p></div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-purple-500/20 flex items-center justify-center"><Satellite size={16} className="text-purple-400" /></div>
            <div><p className="text-xl font-bold text-white tabular-nums">{statsLoading ? '...' : stats?.unique_devices ?? 0}</p><p className="text-xs text-slate-400">Dispositivos</p></div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-blue-500/20 flex items-center justify-center"><Router size={16} className="text-blue-400" /></div>
            <div><p className="text-xl font-bold text-white tabular-nums">{statsLoading ? '...' : stats?.gateways_registered ?? 0}</p><p className="text-xs text-slate-400">GW registrados</p></div>
          </div>
          <div className="card p-4 flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-warning/20 flex items-center justify-center"><Clock size={16} className="text-warning" /></div>
            <div>
              <p className="text-sm font-bold text-white truncate max-w-[100px]">{statsLoading ? '...' : stats?.last_packet ? formatDateTime(stats.last_packet.created_at) : '—'}</p>
              <p className="text-xs text-slate-400">Ultimo</p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center justify-between">
          <div className="flex gap-1 bg-surface-800 rounded-lg p-1 w-fit">
            {[
              { k: 'reader' as Tab, icon: Table, label: 'Lectura' },
              { k: 'gateways' as Tab, icon: Antenna, label: 'Gateways' },
              { k: 'devices' as Tab, icon: Waves, label: 'Dispositivos' },
              { k: 'config' as Tab, icon: Settings, label: 'Config' },
            ].map(({ k, icon: Icon, label }) => (
              <button key={k} onClick={() => setTab(k)}
                className={cn('flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all',
                  tab === k ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-slate-200')} >
                <Icon size={14} />{label}
              </button>
            ))}
          </div>
          <button onClick={() => setConfirmAction({ title: 'Limpiar datos LoRa', msg: 'Se eliminaran todos los paquetes, gateways y dispositivos. Esta accion no se puede deshacer.', onOk: () => clearMutation.mutate() })}
            className="text-xs text-danger hover:text-danger/80 flex items-center gap-1">
            <Trash2 size={13} />Limpiar datos
          </button>
        </div>

        {/* ── Reader Tab ─────────────────────────────────────────── */}
        {tab === 'reader' && <ReaderTab packets={packets} total={total} loading={packetsLoading} limit={limit} setLimit={setLimit} />}

        {/* ── Gateways Tab ───────────────────────────────────────── */}
        {tab === 'gateways' && (
          <GatewaysTab
            gateways={gateways?.gateways ?? []}
            pending={pending?.gateways ?? []}
            loading={gwLoading}
            pendingLoading={pendingLoading}
            onPair={(d) => pairGatewayMutation.mutate(d)}
            onDelete={(id, name) => setConfirmAction({ title: 'Eliminar gateway', msg: `Eliminar "${name || id}"? Se perdera su registro y nombre asignado.`, onOk: () => deleteGatewayMutation.mutate(id) })}
            onUpdate={(gw) => updateGatewayMutation.mutate(gw)}
            pairing={pairGatewayMutation.isPending}
            addOpen={addGwOpen}
            setAddOpen={setAddGwOpen}
          />
        )}

        {/* ── Devices Tab ────────────────────────────────────────── */}
        {tab === 'devices' && (
          <DevicesTab
            devices={devicesData?.devices ?? []}
            loading={devLoading}
            onCreate={(d) => createDeviceMutation.mutate(d)}
            onDelete={(id, name) => setConfirmAction({ title: 'Eliminar dispositivo', msg: `Eliminar "${name || id}"? Se perdera su registro.`, onOk: () => deleteDeviceMutation.mutate(id) })}
            onUpdate={(d) => updateDeviceMutation.mutate(d)}
            creating={createDeviceMutation.isPending}
          />
        )}

        {/* ── Config Tab ─────────────────────────────────────────── */}
        {tab === 'config' && (
          <div className="card p-6 max-w-lg">
            {configLoading ? (
              <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => (<div key={i} className="h-10 bg-surface-700 rounded animate-pulse" />))}</div>
            ) : (
              <form onSubmit={e => { e.preventDefault(); const f = e.currentTarget; configMutation.mutate({ listen_port: (f.elements.namedItem('listen_port') as HTMLInputElement).value, auth_password: (f.elements.namedItem('auth_password') as HTMLInputElement).value, max_packets: (f.elements.namedItem('max_packets') as HTMLInputElement).value }) }} className="space-y-4">
                <div><label className="block text-xs font-semibold text-slate-400 uppercase mb-1.5">Puerto de escucha</label><input name="listen_port" type="number" defaultValue={config?.listen_port ?? '6666'} className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" /><p className="text-xs text-slate-500 mt-1">Puerto HTTPS del listener LoRaWAN</p></div>
                <div><label className="block text-xs font-semibold text-slate-400 uppercase mb-1.5">Password</label><input name="auth_password" type="text" defaultValue={config?.auth_password ?? 'abc1234'} className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-brand-500" /><p className="text-xs text-slate-500 mt-1">Bearer token para el endpoint de ingesta</p></div>
                <div><label className="block text-xs font-semibold text-slate-400 uppercase mb-1.5">Buffer memoria</label><input name="max_packets" type="number" defaultValue={config?.max_packets ?? '500'} className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" /><p className="text-xs text-slate-500 mt-1">Max paquetes en buffer de memoria</p></div>
                <button type="submit" disabled={configMutation.isPending} className="btn-primary w-full flex items-center justify-center gap-2"><Save size={14} />{configMutation.isPending ? 'Guardando...' : 'Guardar configuracion'}</button>
              </form>
            )}
          </div>
        )}
      </div>

      {/* ── Log Popup ─────────────────────────────────────────────── */}
      {logOpen && (
        <div className="fixed bottom-6 right-6 w-[480px] h-[420px] card border border-surface-600 shadow-2xl flex flex-col z-50 animate-in slide-in-from-bottom-4">
          <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700 bg-surface-900 rounded-t-xl">
            <div className="flex items-center gap-2">
              <Activity size={14} className="text-field animate-pulse" />
              <span className="text-sm font-semibold text-white">Trafico LoRaWAN en vivo</span>
              <span className="text-xs text-slate-500">({logLines.length} lineas)</span>
            </div>
            <button onClick={toggleLog} className="text-slate-400 hover:text-white"><X size={16} /></button>
          </div>
          <div ref={logRef} onScroll={handleLogScroll} className="flex-1 overflow-y-auto p-3 space-y-1 font-mono text-xs">
            {logLines.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-500">
                <div className="text-center">
                  <Activity size={20} className="mx-auto mb-2 animate-pulse" />
                  <p>Esperando paquetes...</p>
                </div>
              </div>
            ) : (
              logLines.map((pkt, i) => (
                <div key={`log-${pkt.id}-${i}`} className="flex gap-2 py-0.5 border-b border-surface-800/50 hover:bg-surface-800/30 rounded px-1">
                  <span className="text-slate-500 shrink-0">{formatDateTime(pkt.created_at)}</span>
                  <span className="text-brand-400 shrink-0 font-semibold">{pkt.gateway_name || pkt.gateway_id}</span>
                  <span className={cn(pkt.rssi != null && pkt.rssi > -80 ? 'text-field' : pkt.rssi != null && pkt.rssi > -100 ? 'text-warning' : 'text-danger')}>{pkt.rssi ?? '—'} dBm</span>
                  <span className="text-slate-400">{pkt.device_name || pkt.dev_addr || '—'}</span>
                  {pkt.mtype_str && <span className="text-brand-400/70">{pkt.mtype_str}</span>}
                  <span className="text-slate-500">{pkt.fcnt != null ? `#${pkt.fcnt}` : ''}</span>
                  <span className="text-slate-600 truncate flex-1">{pkt.payload_hex ?? ''}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Confirm Dialog ──────────────────────────────────── */}
      {confirmAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={() => setConfirmAction(null)}>
          <div className="card p-6 max-w-sm w-full mx-4 shadow-2xl border border-surface-600" onClick={e => e.stopPropagation()}>
            <div className="flex items-start gap-3 mb-4">
              <div className="w-9 h-9 rounded-lg bg-danger/20 flex items-center justify-center shrink-0">
                <Trash2 size={16} className="text-danger" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">{confirmAction.title}</h3>
                <p className="text-xs text-slate-400 mt-1">{confirmAction.msg}</p>
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setConfirmAction(null)} className="btn-secondary text-xs">Cancelar</button>
              <button onClick={() => { confirmAction.onOk(); setConfirmAction(null) }} className="bg-danger hover:bg-danger/80 text-white px-4 py-2 rounded-lg text-xs font-medium transition-colors">Eliminar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Reader Tab ────────────────────────────────────────────────────

function ReaderTab({ packets, total, loading, limit, setLimit }: {
  packets: LoraPacket[]; total: number; loading: boolean; limit: number; setLimit: (n: number) => void
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity size={14} className={packets.length > 0 ? 'text-field animate-pulse' : 'text-slate-500'} />
          <span className="text-xs text-slate-400">{loading ? 'Cargando...' : `Mostrando ${packets.length} de ${total} paquetes`}</span>
        </div>
        <div className="flex items-center gap-2">
          {[25, 50, 100, 200].map(n => (
            <button key={n} onClick={() => setLimit(n)} className={cn('px-2 py-0.5 text-xs rounded', limit === n ? 'bg-brand-600 text-white' : 'text-slate-400 hover:text-slate-200 bg-surface-800')}>{n}</button>
          ))}
        </div>
      </div>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-surface-700">
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Timestamp</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Gateway</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Dispositivo</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">RSSI</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">SNR</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Freq</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">SF</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Temp</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Hum</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Bat</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Type</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">FCnt</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Payload</th>
            </tr></thead>
            <tbody>
              {loading ? Array.from({ length: 10 }).map((_, i) => (
                <tr key={i} className="border-b border-surface-700">{Array.from({ length: 13 }).map((_, j) => (<td key={j} className="px-2 py-3"><div className="h-4 bg-surface-700 rounded animate-pulse" /></td>))}</tr>
              )) : packets.length === 0 ? (
                <tr><td colSpan={13} className="px-3 py-12 text-center text-slate-500"><Wifi size={24} className="mx-auto mb-2 opacity-50" />No hay paquetes registrados</td></tr>
              ) : packets.map(pkt => (
                <tr key={pkt.id} className="table-row">
                  <td className="px-2 py-2 text-slate-400 text-xs whitespace-nowrap">{formatDateTime(pkt.created_at)}</td>
                  <td className="px-2 py-2">
                    <span className="text-slate-300 text-xs">{pkt.gateway_name || pkt.gateway_id}</span>
                    {pkt.gateway_name && <span className="text-slate-500 text-[10px] block">{pkt.gateway_id}</span>}
                  </td>
                  <td className="px-2 py-2">
                    {pkt.dev_addr ? <><span className="text-slate-300 text-xs">{pkt.device_name || pkt.dev_addr}</span>
                    {pkt.device_name && <span className="text-slate-500 text-[10px] block font-mono">{pkt.dev_addr}</span>}</> : <span className="text-slate-500 text-xs">—</span>}
                  </td>
                  <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{pkt.rssi != null ? <span className={cn(pkt.rssi > -80 ? 'text-field' : pkt.rssi > -100 ? 'text-warning' : 'text-danger')}>{pkt.rssi} dBm</span> : '—'}</td>
                  <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{pkt.snr != null ? `${pkt.snr.toFixed(1)} dB` : '—'}</td>
                  <td className="px-2 py-2 text-slate-400 text-xs tabular-nums font-mono">{pkt.freq_mhz != null ? `${pkt.freq_mhz.toFixed(1)} MHz` : '—'}</td>
                  <td className="px-2 py-2 text-slate-400 text-xs tabular-nums font-mono">{pkt.sf != null ? `SF${pkt.sf}` : '—'}</td>
                  <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{pkt.temperature != null ? `${pkt.temperature.toFixed(1)}°C` : '—'}</td>
                  <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{pkt.humidity != null ? `${pkt.humidity.toFixed(0)}%` : '—'}</td>
                  <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{pkt.battery != null ? `${pkt.battery.toFixed(0)}%` : '—'}</td>
                  <td className="px-2 py-2">{pkt.mtype_str ? <span className="text-xs px-1.5 py-0.5 rounded bg-brand-600/20 text-brand-400 font-mono">{pkt.mtype_str}</span> : <span className="text-slate-500 text-xs">—</span>}</td>
                  <td className="px-2 py-2 text-slate-400 text-xs tabular-nums font-mono">{pkt.fcnt != null ? pkt.fcnt : '—'}</td>
                  <td className="px-2 py-2 text-slate-500 text-xs font-mono max-w-[100px] truncate">{pkt.payload_hex ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ── Gateways Tab ──────────────────────────────────────────────────

function GatewaysTab({ gateways, pending, loading, pendingLoading, onPair, onDelete, onUpdate, pairing, addOpen, setAddOpen }: {
  gateways: LoraGateway[]; pending: LoraPendingGateway[]; loading: boolean; pendingLoading: boolean;
  onPair: (d: { gateway_id: string; pairing_code: string; name: string }) => void;
  onDelete: (id: string, name?: string | null) => void; onUpdate: (d: { gateway_id: string; name?: string; location?: string; notes?: string }) => void;
  pairing: boolean;
  addOpen: boolean; setAddOpen: (v: boolean) => void;
}) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editLoc, setEditLoc] = useState('')
  const [editNotes, setEditNotes] = useState('')

  // Estado del modal — se reinicia cada vez que se abre
  const [addGwId, setAddGwId] = useState('')
  const [addName, setAddName] = useState('')
  const [addCode, setAddCode] = useState('')

  const startEdit = (gw: LoraGateway) => {
    setEditingId(gw.gateway_id)
    setEditName(gw.name || '')
    setEditLoc(gw.location || '')
    setEditNotes(gw.notes || '')
  }
  const cancelEdit = () => setEditingId(null)
  const saveEdit = (gwId: string) => {
    onUpdate({ gateway_id: gwId, name: editName, location: editLoc, notes: editNotes })
    setEditingId(null)
  }

  const openPairFor = (gw: LoraPendingGateway) => {
    setAddGwId(gw.gateway_id)
    setAddName('')
    setAddCode('')
    setAddOpen(true)
  }

  const openAdd = () => {
    setAddGwId('')
    setAddName('')
    setAddCode('')
    setAddOpen(true)
  }

  const closeAdd = () => {
    setAddOpen(false)
    setAddGwId('')
    setAddName('')
    setAddCode('')
  }

  const submitAdd = (e: React.FormEvent) => {
    e.preventDefault()
    if (!addGwId.trim() || !addCode.trim() || !addName.trim()) return
    onPair({ gateway_id: addGwId.trim(), pairing_code: addCode.trim(), name: addName.trim() })
  }

  return (
    <div className="space-y-4">
      {/* Banner: gateways pendientes de pairing */}
      {pending && pending.length > 0 && (
        <div className="card p-4 border border-warning/40 bg-warning/5">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-lg bg-warning/20 flex items-center justify-center shrink-0">
              <KeyRound size={16} className="text-warning" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white mb-1">Gateways pendientes de registro</p>
              <p className="text-xs text-slate-400 mb-3">
                {pending.length} gateway{pending.length !== 1 ? 's' : ''} con codigo de pairing activo.
                Hace clic en <strong>Emparejar</strong> y completa el codigo para registrarlo.
              </p>
              <div className="space-y-2">
                {pendingLoading ? (
                  <div className="h-10 bg-surface-800 rounded animate-pulse" />
                ) : pending.map(p => (
                  <div key={p.gateway_id} className="flex items-center gap-3 bg-surface-900/60 rounded-lg p-2.5 border border-surface-700">
                    <div className="flex-1 min-w-0">
                      <p className="font-mono text-xs text-white truncate">{p.gateway_id}</p>
                      <p className="text-[10px] text-slate-500 flex items-center gap-2">
                        {p.wifi_ssid && <span><Navigation size={9} className="inline mr-0.5" />{p.wifi_ssid}</span>}
                        {p.last_seen && <span>visto {formatDateTime(p.last_seen)}</span>}
                        {p.pairing_expires_at && (
                          <span className="text-warning">expira {formatDateTime(p.pairing_expires_at)}</span>
                        )}
                      </p>
                    </div>
                    <button onClick={() => openPairFor(p)} className="btn-primary text-xs flex items-center gap-1.5 shrink-0">
                      <KeyRound size={12} />Emparejar
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="card overflow-hidden">
        {/* Header con botón de alta */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-700 bg-surface-900/50">
          <div className="flex items-center gap-2">
            <Antenna size={14} className="text-brand-400" />
            <span className="text-sm font-semibold text-white">Gateways registrados</span>
            <span className="text-xs text-slate-500">({gateways.length})</span>
          </div>
          <button onClick={openAdd} className="btn-primary text-sm flex items-center gap-1.5">
            <Plus size={14} />Agregar nuevo Gateway
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-surface-700">
              <th className="px-1 py-2 text-left text-xs font-semibold text-slate-400 uppercase w-6"></th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Gateway ID</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Nombre</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">GPS</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">WiFi</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Bateria</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Uptime</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Pkts</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Ultima</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase w-24"></th>
            </tr></thead>
            <tbody>
              {loading ? Array.from({ length: 3 }).map((_, i) => (<tr key={i} className="border-b border-surface-700">{Array.from({ length: 9 }).map((_, j) => (<td key={j} className="px-2 py-3"><div className="h-4 bg-surface-700 rounded animate-pulse" /></td>))}</tr>))
              : gateways.length === 0 ? (
                <tr><td colSpan={9} className="px-3 py-12 text-center text-slate-500">
                  <div className="max-w-sm mx-auto">
                    <KeyRound size={28} className="mx-auto mb-2 opacity-50" />
                    <p className="text-sm text-slate-400">No hay gateways registrados todavia.</p>
                    <p className="text-xs text-slate-500 mt-1">Hace clic en <strong>Agregar nuevo Gateway</strong> y completa el codigo de pairing que muestra el dispositivo.</p>
                  </div>
                </td></tr>
              ) : gateways.map(gw => {
                const isEditing = editingId === gw.gateway_id
                const online = !!gw.online
                return (
                  <tr key={gw.id} className={cn('table-row', isEditing && 'bg-surface-800/50')}>
                    <td className="px-1 py-2">
                      <span className={cn('w-2 h-2 rounded-full block', online ? 'bg-field animate-pulse' : 'bg-slate-600')} title={online ? 'Conectado' : 'Desconectado >1h'} />
                    </td>
                    <td className="px-2 py-2 font-mono text-white text-xs">{gw.gateway_id}</td>
                    <td className="px-2 py-2">
                      {isEditing ? (
                        <input value={editName} onChange={e => setEditName(e.target.value)}
                          className="bg-surface-700 border border-surface-600 rounded px-2 py-1 text-xs text-white w-full focus:outline-none focus:border-brand-500" />
                      ) : (
                        <span className="text-slate-300 text-xs">{gw.name || <span className="text-slate-500 italic">Sin nombre</span>}</span>
                      )}
                    </td>
                    <td className="px-2 py-2">
                      {gw.lat != null && gw.lon != null ? (
                        <span className="flex items-center gap-1 text-xs text-field font-mono">
                          <MapPin size={11} />{gw.lat.toFixed(4)},{gw.lon.toFixed(4)}
                        </span>
                      ) : <span className="text-slate-500 text-xs">—</span>}
                    </td>
                    <td className="px-2 py-2">
                      {gw.wifi_ssid ? (
                        <span className="flex flex-col text-xs gap-0.5">
                          <span className="flex items-center gap-1">
                            <Navigation size={11} className={cn(gw.wifi_rssi != null && gw.wifi_rssi > -60 ? 'text-field' : 'text-warning')} />
                            <span className="text-slate-300">{gw.wifi_ssid}</span>
                            {gw.wifi_rssi != null && <span className="text-slate-500 tabular-nums">{gw.wifi_rssi}dBm</span>}
                          </span>
                          {gw.wifi_ip && <span className="text-[10px] text-slate-500 font-mono ml-4">{gw.wifi_ip}</span>}
                        </span>
                      ) : <span className="text-slate-500 text-xs">—</span>}
                    </td>
                    <td className="px-2 py-2">
                      {gw.battery_pct != null ? (
                        <span className={cn('flex items-center gap-1 text-xs tabular-nums',
                          gw.battery_pct <= 20 ? 'text-danger' : gw.battery_pct <= 50 ? 'text-warning' : 'text-field')}>
                          {gw.battery_pct <= 20 ? <BatteryLow size={13} /> : gw.battery_pct >= 80 ? <BatteryFull size={13} /> : <Battery size={13} />}
                          {gw.battery_pct.toFixed(0)}%
                        </span>
                      ) : <span className="text-slate-500 text-xs">—</span>}
                    </td>
                    <td className="px-2 py-2 text-slate-400 text-xs tabular-nums font-mono">
                      {gw.uptime_s != null ? `${Math.floor(gw.uptime_s / 3600)}h${Math.floor((gw.uptime_s % 3600) / 60)}m` : '—'}
                    </td>
                    <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{gw.pkts_total != null ? gw.pkts_total : gw.total_packets ?? 0}</td>
                    <td className="px-2 py-2 text-slate-400 text-xs whitespace-nowrap">
                      {(gw.updated_at || gw.last_seen) ? formatDateTime(gw.updated_at || gw.last_seen) : 'nunca'}
                    </td>
                    <td className="px-2 py-2">
                      <div className="flex items-center gap-1">
                        {isEditing ? (
                          <>
                            <button onClick={() => saveEdit(gw.gateway_id)} className="text-field hover:text-field/80 p-1" title="Guardar"><Check size={14} /></button>
                            <button onClick={cancelEdit} className="text-slate-400 hover:text-white p-1" title="Cancelar"><X size={14} /></button>
                          </>
                        ) : (
                          <button onClick={() => startEdit(gw)} className="text-slate-400 hover:text-brand-400 p-1" title="Editar"><Pencil size={14} /></button>
                        )}
                        <button onClick={() => onDelete(gw.gateway_id, gw.name)} className="text-slate-500 hover:text-danger p-1"><Trash2 size={14} /></button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal único de "Agregar nuevo Gateway" (pairing) */}
      {addOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={closeAdd}>
          <form onSubmit={submitAdd} className="card p-6 max-w-lg w-full shadow-2xl border border-surface-600 max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-start gap-3 mb-5">
              <div className="w-10 h-10 rounded-lg bg-brand-600/20 flex items-center justify-center shrink-0">
                <Antenna size={18} className="text-brand-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-base font-semibold text-white">Agregar nuevo Gateway</h3>
                <p className="text-xs text-slate-400 mt-1">
                  Para registrar un gateway necesitas el codigo de pairing de 6 digitos
                  que muestra el dispositivo fisico en su pantalla o portal web.
                </p>
              </div>
              <button type="button" onClick={closeAdd} className="text-slate-400 hover:text-white shrink-0">
                <X size={18} />
              </button>
            </div>

            {/* Pasos */}
            <div className="bg-surface-900/60 border border-surface-700 rounded-lg p-3 mb-5 text-xs text-slate-300 space-y-1.5">
              <p className="font-semibold text-slate-200 mb-2">Como obtener el codigo:</p>
              <p><span className="text-brand-400 font-mono">1.</span> Enciende el gateway. Si nunca fue registrado, mostrara un codigo de 6 digitos en su pantalla.</p>
              <p><span className="text-brand-400 font-mono">2.</span> Si no aparece, conecta al WiFi <span className="font-mono">Exalink-Gateway-XXXX</span> y abrí <span className="font-mono">http://192.168.4.1</span>.</p>
              <p><span className="text-brand-400 font-mono">3.</span> El codigo vence en 10 minutos. Si expira, pulsa <em>Regenerar codigo</em>.</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase mb-1.5">
                  Gateway ID <span className="text-danger">*</span>
                </label>
                <input value={addGwId} onChange={e => setAddGwId(e.target.value)} required
                  placeholder="ABCD12345678 (16 caracteres hex)"
                  className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-brand-500" />
                <p className="text-[11px] text-slate-500 mt-1">
                  Lo encontras en la pantalla del gateway, en el portal web, o en la etiqueta del equipo.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase mb-1.5">
                  Codigo de Pairing <span className="text-danger">*</span>
                </label>
                <input value={addCode} onChange={e => setAddCode(e.target.value.replace(/\D/g, '').slice(0, 6))} required
                  placeholder="123456" maxLength={6} inputMode="numeric"
                  className="w-full bg-surface-800 border-2 border-surface-700 rounded-lg px-3 py-3 text-2xl text-white font-mono tracking-[0.4em] text-center focus:outline-none focus:border-brand-500" />
                <p className="text-[11px] text-slate-500 mt-1">
                  6 digitos que muestra el gateway en su pantalla. Vence en 10 minutos.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase mb-1.5">
                  Nombre para identificar <span className="text-danger">*</span>
                </label>
                <input value={addName} onChange={e => setAddName(e.target.value)} required
                  placeholder="Gateway Norte - Potrero 3"
                  className="w-full bg-surface-800 border border-surface-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
              </div>
            </div>

            <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-surface-700">
              <button type="button" onClick={closeAdd} className="btn-secondary text-sm">Cancelar</button>
              <button type="submit"
                disabled={pairing || !addGwId.trim() || !addCode.trim() || !addName.trim()}
                className="btn-primary text-sm flex items-center gap-1.5">
                {pairing
                  ? <><RefreshCw size={13} className="animate-spin" />Registrando...</>
                  : <><KeyRound size={13} />Registrar Gateway</>}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}

// ── Devices Tab ───────────────────────────────────────────────────

function DevicesTab({ devices, loading, onCreate, onDelete, onUpdate, creating }: {
  devices: LoraDevice[]; loading: boolean; onCreate: (d: Partial<LoraDevice>) => void;
  onDelete: (id: string, name?: string | null) => void;
  onUpdate: (d: { dev_addr: string; name?: string; device_type?: string; refresh_freq_s?: number }) => void;
  creating: boolean
}) {
  const [editingAddr, setEditingAddr] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editType, setEditType] = useState('sensor')
  const [editFreq, setEditFreq] = useState('60')
  const formRef = useRef<HTMLFormElement>(null)

  const startEdit = (dev: LoraDevice) => { setEditingAddr(dev.dev_addr); setEditName(dev.name || ''); setEditType(dev.device_type); setEditFreq(String(dev.refresh_freq_s ?? 60)) }
  const cancelEdit = () => setEditingAddr(null)
  const saveEdit = (devAddr: string) => { onUpdate({ dev_addr: devAddr, name: editName, device_type: editType, refresh_freq_s: Number(editFreq) || 60 }); setEditingAddr(null) }

  const statusDot = (online: number) => {
    if (online === 1) return <span className="w-2 h-2 rounded-full bg-field animate-pulse block" title="Conectado" />
    if (online === 2) return <span className="w-2 h-2 rounded-full bg-warning animate-pulse block" title="Senal debil" />
    return <span className="w-2 h-2 rounded-full bg-slate-600 block" title="Desconectado" />
  }

  return (
    <div className="space-y-4">
      <form ref={formRef} onSubmit={e => { e.preventDefault(); const f = e.currentTarget; onCreate({ dev_addr: (f.elements.namedItem('dev_addr') as HTMLInputElement).value, name: (f.elements.namedItem('dev_name') as HTMLInputElement).value, dev_eui: (f.elements.namedItem('dev_eui') as HTMLInputElement).value, device_type: (f.elements.namedItem('dev_type') as HTMLSelectElement).value, gateway_id: (f.elements.namedItem('dev_gw') as HTMLInputElement).value, refresh_freq_s: Number((f.elements.namedItem('dev_freq') as HTMLInputElement).value) || 60 }); f.reset() }}
        className="card p-4 flex flex-wrap items-end gap-3">
        <div className="flex-1 min-w-[130px]"><label className="block text-xs text-slate-400 mb-1">DevAddr *</label><input name="dev_addr" required placeholder="26012345" className="w-full bg-surface-800 border border-surface-700 rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-brand-500" /></div>
        <div className="flex-1 min-w-[100px]"><label className="block text-xs text-slate-400 mb-1">Nombre</label><input name="dev_name" placeholder="Collar 01" className="w-full bg-surface-800 border border-surface-700 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" /></div>
        <div className="w-[100px]"><label className="block text-xs text-slate-400 mb-1">Tipo</label><select name="dev_type" className="w-full bg-surface-800 border border-surface-700 rounded px-2 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
          {['sensor','collar','tag','tanque','humedad','animal','gateway','other'].map(t => <option key={t} value={t}>{t}</option>)}
        </select></div>
        <div className="w-[75px]"><label className="block text-xs text-slate-400 mb-1">Freq (s)</label><input name="dev_freq" type="number" defaultValue="60" min="5" className="w-full bg-surface-800 border border-surface-700 rounded px-2 py-2 text-sm text-white focus:outline-none focus:border-brand-500" /></div>
        <div className="flex-1 min-w-[100px]"><label className="block text-xs text-slate-400 mb-1">Gateway ID</label><input name="dev_gw" placeholder="GW-001" className="w-full bg-surface-800 border border-surface-700 rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-brand-500" /></div>
        <button type="submit" disabled={creating} className="btn-primary flex items-center gap-1.5 text-sm h-10"><Plus size={14} />{creating ? 'Registrando...' : 'Registrar'}</button>
      </form>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-surface-700">
              <th className="px-1 py-2 uppercase w-6"></th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">ID Interno</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Nombre</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Tipo</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">HW</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Freq</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">GPS</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">WiFi</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Temp</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Hum</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Bateria</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Paq.</th>
              <th className="px-2 py-2 text-left text-xs font-semibold text-slate-400 uppercase">Ultima</th>
              <th className="px-2 py-2 uppercase w-20"></th>
            </tr></thead>
            <tbody>
              {loading ? Array.from({ length: 3 }).map((_, i) => (<tr key={i} className="border-b border-surface-700">{Array.from({ length: 14 }).map((_, j) => (<td key={j} className="px-2 py-3"><div className="h-4 bg-surface-700 rounded animate-pulse" /></td>))}</tr>))
              : devices.length === 0 ? (
                <tr><td colSpan={14} className="px-3 py-12 text-center text-slate-500">No hay dispositivos registrados</td></tr>
              ) : devices.map(dev => {
                const isEditing = editingAddr === dev.dev_addr
                return (
                <tr key={dev.id} className={cn('table-row', isEditing && 'bg-surface-800/50')}>
                  <td className="px-1 py-2">{statusDot(dev.online)}</td>
                  <td className="px-2 py-2 font-mono text-white text-xs">{dev.dev_addr}</td>
                  <td className="px-2 py-2">
                    {isEditing ? <input value={editName} onChange={e => setEditName(e.target.value)} className="bg-surface-700 border border-surface-600 rounded px-2 py-1 text-xs text-white w-full focus:outline-none focus:border-brand-500" />
                    : <span className="text-slate-300 text-xs">{dev.name || <span className="text-slate-500 italic">Sin nombre</span>}</span>}
                  </td>
                  <td className="px-2 py-2">
                    {isEditing ? <select value={editType} onChange={e => setEditType(e.target.value)} className="bg-surface-700 border border-surface-600 rounded px-1 py-1 text-xs text-white focus:outline-none focus:border-brand-500">
                      {['sensor','collar','tag','tanque','humedad','animal','gateway','other'].map(t => <option key={t} value={t}>{t}</option>)}
                    </select> : <span className="text-slate-400 text-xs capitalize">{dev.device_type}</span>}
                  </td>
                  <td className="px-2 py-2 text-slate-400 text-xs font-mono">{dev.hw_version || '—'}</td>
                  <td className="px-2 py-2">
                    {isEditing ? <input value={editFreq} onChange={e => setEditFreq(e.target.value)} type="number" min="5" className="bg-surface-700 border border-surface-600 rounded px-2 py-1 text-xs text-white w-16 focus:outline-none focus:border-brand-500" />
                    : <span className="text-slate-400 text-xs tabular-nums">{dev.refresh_freq_s ?? 60}s</span>}
                  </td>
                  <td className="px-2 py-2">
                    {dev.lat != null && dev.lon != null ? (
                      <span className="flex items-center gap-1 text-xs font-mono">
                        <MapPin size={11} className={dev.gps_fresh === 1 ? 'text-field' : 'text-slate-500'} />
                        <span className={dev.gps_fresh === 1 ? 'text-field' : 'text-slate-500'}>{dev.lat.toFixed(4)},{dev.lon.toFixed(4)}</span>
                        {dev.gps_fresh !== 1 && <span className="text-[9px] text-slate-600 ml-0.5">(cache)</span>}
                      </span>
                    ) : <span className="text-slate-500 text-xs">—</span>}
                  </td>
                  <td className="px-2 py-2">{dev.wifi_ssid ? <span className="flex items-center gap-1 text-xs"><Navigation size={11} className={cn(dev.wifi_rssi != null && dev.wifi_rssi > -60 ? 'text-field' : 'text-warning')} /><span className="text-slate-300">{dev.wifi_ssid}</span>{dev.wifi_rssi != null && <span className="text-slate-500 tabular-nums">{dev.wifi_rssi}dBm</span>}</span> : <span className="text-slate-500 text-xs">—</span>}</td>
                  <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{dev.temperature != null ? <span className={cn(dev.temperature > 38 ? 'text-danger' : dev.temperature < 5 ? 'text-blue-400' : 'text-slate-300')}>{dev.temperature.toFixed(1)}°C</span> : '—'}</td>
                  <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{dev.humidity != null ? `${dev.humidity.toFixed(0)}%` : '—'}</td>
                  <td className="px-2 py-2">{dev.battery_pct != null ? <span className={cn('flex items-center gap-1 text-xs tabular-nums', dev.battery_pct <= 20 ? 'text-danger' : dev.battery_pct <= 50 ? 'text-warning' : 'text-field')}>{dev.battery_pct <= 20 ? <BatteryLow size={13} /> : dev.battery_pct >= 80 ? <BatteryFull size={13} /> : <Battery size={13} />}{dev.battery_pct.toFixed(0)}%</span> : <span className="text-slate-500 text-xs">—</span>}</td>
                  <td className="px-2 py-2 text-slate-400 text-xs tabular-nums">{dev.total_packets ?? 0}</td>
                  <td className="px-2 py-2 text-slate-400 text-xs whitespace-nowrap">{(dev.updated_at || dev.last_seen) ? formatDateTime(dev.updated_at || dev.last_seen) : 'nunca'}</td>
                  <td className="px-2 py-2">
                    <div className="flex items-center gap-1">
                      {isEditing ? <><button onClick={() => saveEdit(dev.dev_addr)} className="text-field hover:text-field/80 p-1"><Check size={14} /></button><button onClick={cancelEdit} className="text-slate-400 hover:text-white p-1"><X size={14} /></button></> : <button onClick={() => startEdit(dev)} className="text-slate-400 hover:text-brand-400 p-1"><Pencil size={14} /></button>}
                      <button onClick={() => onDelete(dev.dev_addr, dev.name)} className="text-slate-500 hover:text-danger p-1"><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>)})}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
