import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { AlertSeverity, AlertType, AnimalStatus, DeviceType } from '@/types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function tempMin(dataMin: number, defaultsLow = -10, padding = 2): number {
  if (Number.isNaN(dataMin)) return defaultsLow
  return dataMin < defaultsLow ? dataMin - padding : defaultsLow
}

export function tempMax(dataMax: number, defaultsHigh = 50, padding = 2): number {
  if (Number.isNaN(dataMax)) return defaultsHigh
  return dataMax > defaultsHigh ? dataMax + padding : defaultsHigh
}

export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  return new Date(dateStr).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return 'nunca'
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'hace un momento'
  if (mins < 60) return `hace ${mins}m`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `hace ${hrs}h`
  return `hace ${Math.floor(hrs / 24)}d`
}

export const severityColor: Record<AlertSeverity, string> = {
  info: 'text-blue-400 bg-blue-400/10 border-blue-400/30',
  warning: 'text-warning bg-warning/10 border-warning/30',
  critical: 'text-danger bg-danger/10 border-danger/30',
}

export const alertTypeLabel: Record<AlertType, string> = {
  outside_geofence: 'Fuera de geocerca',
  outside_field: 'Fuera de campo',
  immobile: 'Animal inmóvil',
  low_battery: 'Batería baja',
  device_offline: 'Dispositivo offline',
  prolonged_disconnect: 'Desconexión prolongada',
  abnormal_activity: 'Actividad anormal',
  possible_heat: 'Posible celo',
  possible_birth: 'Posible parto',
  vaccine_due: 'Vacuna pendiente',
  temperature_low: 'Temp. baja',
  temperature_high: 'Temp. alta',
  manual: 'Manual',
}

export const animalStatusLabel: Record<AnimalStatus, string> = {
  active: 'Activo',
  sold: 'Vendido',
  dead: 'Muerto',
  sick: 'Enfermo',
  quarantine: 'Cuarentena',
  transferred: 'Transferido',
}

export const animalStatusColor: Record<AnimalStatus, string> = {
  active: 'text-field bg-field/10',
  sold: 'text-blue-400 bg-blue-400/10',
  dead: 'text-surface-200 bg-surface-700',
  sick: 'text-danger bg-danger/10',
  quarantine: 'text-warning bg-warning/10',
  transferred: 'text-purple-400 bg-purple-400/10',
}

export const deviceTypeLabel: Record<DeviceType, string> = {
  gps_collar: 'Collar GPS',
  gps_tag: 'Caravana GPS',
  sensor: 'Sensor',
  gateway: 'Gateway',
}
