import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { LoraDevice } from '@/types'

interface DeviceState {
  online: boolean
  battery: number | null
  name: string
}

function useDeviceMonitor() {
  const prevRef = useRef<Map<string, DeviceState>>(new Map())
  const notifiedRef = useRef<Set<string>>(new Set())

  const { data } = useQuery<{ devices: LoraDevice[] }>({
    queryKey: ['device-monitor'],
    queryFn: () => api.get('/lora/devices').then(r => r.data),
    refetchInterval: 15_000,
  })

  const sendEvent = async (devAddr: string, event: string, batteryPct?: number | null) => {
    try {
      await api.post('/alerts/device-event', {
        dev_addr: devAddr,
        event,
        battery_pct: batteryPct ?? null,
      })
    } catch {
      // silently ignore
    }
  }

  useEffect(() => {
    if (!data?.devices) return

    const prev = prevRef.current
    const now = new Map<string, DeviceState>()

    for (const d of data.devices) {
      const isOnline = d.online >= 1
      const bat = d.battery_pct ?? null
      const name = d.name || d.dev_addr
      const key = d.dev_addr
      now.set(key, { online: isOnline, battery: bat, name })

      const old = prev.get(key)

      // Se fue offline
      if (old && old.online && !isOnline) {
        const nkey = `offline-${key}`
        if (!notifiedRef.current.has(nkey)) {
          toast.error(`${name} se fue offline`, { icon: '📡', duration: 5000 })
          sendEvent(key, 'offline')
          notifiedRef.current.add(nkey)
        }
      }

      // Volvió online
      if (old && !old.online && isOnline) {
        toast.success(`${name} volvió online`, { icon: '✅', duration: 4000 })
        sendEvent(key, 'online')
        notifiedRef.current.delete(`offline-${key}`)
        notifiedRef.current.delete(`lowbat-${key}`)
      }

      // Batería crítica
      if (bat !== null && bat <= 10) {
        if (!old || (old.battery !== null && old.battery > 10)) {
          const nkey = `lowbat-${key}`
          if (!notifiedRef.current.has(nkey)) {
            toast(`${name} batería crítica: ${Math.round(bat)}%`, {
              icon: '🔋',
              duration: 8000,
              style: { background: '#451a03', color: '#fbbf24', border: '1px solid #78350f' },
            })
            sendEvent(key, 'low_battery', bat)
            notifiedRef.current.add(nkey)
          }
        }
      }

      // Batería recuperada
      if (old && old.battery !== null && old.battery <= 10 && bat !== null && bat > 15) {
        notifiedRef.current.delete(`lowbat-${key}`)
      }
    }

    prevRef.current = now
  }, [data])
}

export default useDeviceMonitor
