import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'

interface KPICardProps {
  title: string
  value: number | string
  icon: LucideIcon
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'slate'
  subtitle?: string
  alert?: boolean
}

const colorMap = {
  blue: 'text-brand-400 bg-brand-400/10 border-brand-400/20',
  green: 'text-field bg-field/10 border-field/20',
  yellow: 'text-warning bg-warning/10 border-warning/20',
  red: 'text-danger bg-danger/10 border-danger/20',
  purple: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
  slate: 'text-slate-400 bg-slate-400/10 border-slate-400/20',
}

const iconBg = {
  blue: 'bg-brand-600/20 text-brand-400',
  green: 'bg-field/20 text-field',
  yellow: 'bg-warning/20 text-warning',
  red: 'bg-danger/20 text-danger',
  purple: 'bg-purple-600/20 text-purple-400',
  slate: 'bg-slate-600/20 text-slate-400',
}

export default function KPICard({ title, value, icon: Icon, color = 'blue', subtitle, alert }: KPICardProps) {
  return (
    <div className={cn(
      'card p-4 flex items-start gap-4 transition-all',
      alert && Number(value) > 0 ? `border ${colorMap[color]}` : 'hover:border-surface-600'
    )}>
      <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0', iconBg[color])}>
        <Icon size={18} />
      </div>
      <div className="min-w-0">
        <p className="text-2xl font-bold text-white tabular-nums">{value}</p>
        <p className="text-xs text-slate-400 mt-0.5 truncate">{title}</p>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}
