import { useState, useEffect } from 'react'
import { RefreshCw, ArrowDown, ArrowUp, Clock, AlertTriangle, CheckCircle } from 'lucide-react'
import { fullSync, getLastSync, getPendingCount, type SyncResult } from '@/lib/sync'
import { db, type SyncLog } from '@/lib/db'
import { cn } from '@/lib/utils'
import toast from 'react-hot-toast'

function formatDuration(ms: number) {
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(1)}s`
}

function formatTs(iso: string) {
  return new Date(iso).toLocaleString('es-AR', {
    day: '2-digit', month: '2-digit', year: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

export default function SyncTab() {
  const [syncing, setSyncing] = useState(false)
  const [lastResult, setLastResult] = useState<SyncResult | null>(null)
  const [lastLog, setLastLog] = useState<SyncLog | undefined>()
  const [pending, setPending] = useState(0)
  const [localCount, setLocalCount] = useState(0)
  const [logs, setLogs] = useState<SyncLog[]>([])

  const refresh = async () => {
    const [llog, pend, count, allLogs] = await Promise.all([
      getLastSync(),
      getPendingCount(),
      db.animals.count(),
      db.syncLogs.orderBy('id').reverse().limit(20).toArray(),
    ])
    setLastLog(llog)
    setPending(pend)
    setLocalCount(count)
    setLogs(allLogs)
  }

  useEffect(() => { refresh() }, [])

  const handleSync = async () => {
    if (!navigator.onLine) {
      toast.error('Sin conexión — no se puede sincronizar')
      return
    }
    setSyncing(true)
    try {
      const result = await fullSync()
      setLastResult(result)
      await refresh()
      if (result.errors > 0) {
        toast.error(`Sincronización parcial — ${result.errors} error(s)`)
      } else {
        toast.success(`Sincronizado: ↓${result.pulled} ↑${result.pushed}`)
      }
    } catch (e) {
      toast.error('Error de sincronización')
    } finally {
      setSyncing(false)
    }
  }

  return (
    <div className="p-4 space-y-4 max-w-lg mx-auto">
      {/* Status cards */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-surface-800 border border-surface-700 rounded-xl px-4 py-3 text-center">
          <p className="text-2xl font-bold text-white">{localCount}</p>
          <p className="text-xs text-slate-400 mt-0.5">Animales locales</p>
        </div>
        <div className={cn(
          'border rounded-xl px-4 py-3 text-center',
          pending > 0 ? 'bg-amber-900/20 border-amber-700/50' : 'bg-surface-800 border-surface-700'
        )}>
          <p className={cn('text-2xl font-bold', pending > 0 ? 'text-amber-400' : 'text-white')}>{pending}</p>
          <p className={cn('text-xs mt-0.5', pending > 0 ? 'text-amber-500' : 'text-slate-400')}>
            {pending === 1 ? 'Registro pendiente' : 'Registros pendientes'}
          </p>
        </div>
      </div>

      {/* Last sync */}
      {lastLog && (
        <div className="bg-surface-800 border border-surface-700 rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-2">
            <Clock size={14} className="text-slate-500" />
            <p className="text-xs text-slate-400 font-medium">Última sincronización</p>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-white">{formatTs(lastLog.timestamp)}</p>
              <p className="text-xs text-slate-500 mt-0.5">
                ↓{lastLog.records_in} recibidos · ↑{lastLog.records_out} enviados · {formatDuration(lastLog.duration_ms)}
              </p>
            </div>
            {lastLog.status === 'success' ? (
              <CheckCircle size={18} className="text-emerald-400" />
            ) : lastLog.status === 'partial' ? (
              <AlertTriangle size={18} className="text-amber-400" />
            ) : (
              <AlertTriangle size={18} className="text-red-400" />
            )}
          </div>
          {lastLog.error && (
            <p className="text-xs text-red-400 mt-1">{lastLog.error}</p>
          )}
        </div>
      )}

      {/* Last result (after sync) */}
      {lastResult && (
        <div className={cn(
          'border rounded-xl px-4 py-3',
          lastResult.errors > 0 ? 'bg-amber-900/20 border-amber-700/50' : 'bg-emerald-900/20 border-emerald-700/50'
        )}>
          <p className="text-xs font-medium text-slate-300 mb-2">Resultado</p>
          <div className="flex gap-4 text-sm">
            <div className="flex items-center gap-1.5 text-emerald-300">
              <ArrowDown size={14} />
              <span>{lastResult.pulled} descargados</span>
            </div>
            <div className="flex items-center gap-1.5 text-brand-300">
              <ArrowUp size={14} />
              <span>{lastResult.pushed} enviados</span>
            </div>
            {lastResult.errors > 0 && (
              <div className="flex items-center gap-1.5 text-red-400">
                <AlertTriangle size={14} />
                <span>{lastResult.errors} errores</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Sync button */}
      <button
        onClick={handleSync}
        disabled={syncing}
        className={cn(
          'w-full flex items-center justify-center gap-2 py-3.5 rounded-xl text-sm font-semibold transition-colors',
          syncing
            ? 'bg-brand-700/50 text-brand-400/60 cursor-not-allowed'
            : 'bg-brand-600 hover:bg-brand-500 text-white'
        )}
      >
        <RefreshCw size={16} className={syncing ? 'animate-spin' : ''} />
        {syncing ? 'Sincronizando...' : 'Sincronizar ahora'}
      </button>

      <p className="text-xs text-center text-slate-600">
        Descarga animales del servidor y envía los cambios pendientes.
        Funciona solo con conexión.
      </p>

      {/* Log history */}
      {logs.length > 1 && (
        <div>
          <p className="text-xs text-slate-500 font-medium mb-2">Historial</p>
          <div className="space-y-1.5">
            {logs.slice(1).map((log) => (
              <div key={log.id} className="flex items-center justify-between px-3 py-2 bg-surface-800 rounded-lg text-xs">
                <span className="text-slate-400">{formatTs(log.timestamp)}</span>
                <div className="flex items-center gap-3">
                  <span className="text-slate-500">↓{log.records_in} ↑{log.records_out}</span>
                  {log.status === 'success'
                    ? <CheckCircle size={12} className="text-emerald-400" />
                    : <AlertTriangle size={12} className="text-amber-400" />
                  }
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
