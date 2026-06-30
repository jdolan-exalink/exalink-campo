import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import type { Alert, AlertConfig } from '@/types'

const SEEN_KEY = 'exalink:alert-notifications:seen'

function loadSeen(): Set<string> {
  try {
    const raw = localStorage.getItem(SEEN_KEY)
    if (!raw) return new Set()
    const arr = JSON.parse(raw) as string[]
    return new Set(arr.slice(-500))
  } catch {
    return new Set()
  }
}

function saveSeen(set: Set<string>) {
  try {
    const arr = Array.from(set).slice(-500)
    localStorage.setItem(SEEN_KEY, JSON.stringify(arr))
  } catch {
    /* ignore */
  }
}

/**
 * Emite notificaciones del navegador para nuevas alertas abiertas, respetando
 * la configuración `browser_notify` de cada tipo de alerta.
 */
function useAlertNotifications() {
  const seenRef = useRef<Set<string>>(loadSeen())

  const { data: configs = [] } = useQuery<AlertConfig[]>({
    queryKey: ['alert-configs'],
    queryFn: () => api.get('/alert-configs').then(r => r.data),
    staleTime: 60_000,
  })

  const { data: alerts = [] } = useQuery<Alert[]>({
    queryKey: ['alert-notifications'],
    queryFn: () =>
      api
        .get('/alerts?status=open&limit=20')
        .then(r => r.data as Alert[]),
    refetchInterval: 20_000,
  })

  useEffect(() => {
    if (!alerts.length) return

    const notifyByType = new Map(
      configs
        .filter(c => c.enabled && c.browser_notify)
        .map(c => [c.alert_type, c])
    )

    let changed = false
    for (const a of alerts) {
      if (seenRef.current.has(a.id)) continue
      seenRef.current.add(a.id)
      changed = true

      const cfg = notifyByType.get(a.alert_type)
      if (!cfg) continue // tipo desactivado o sin notif browser

      if ('Notification' in window && Notification.permission === 'granted') {
        try {
          const n = new Notification(a.title, {
            body: a.message ?? '',
            tag: a.id,
          })
          n.onclick = () => {
            window.focus()
            n.close()
          }
        } catch {
          /* ignore */
        }
      }
    }

    if (changed) saveSeen(seenRef.current)
  }, [alerts, configs])
}

export default useAlertNotifications

/** Pide permiso de notificaciones del navegador si no está decidido. */
export function ensureNotificationPermission() {
  if (!('Notification' in window)) return
  if (Notification.permission === 'default') {
    try {
      Notification.requestPermission()
    } catch {
      /* ignore */
    }
  }
}
