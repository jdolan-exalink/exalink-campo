import { useState, useEffect } from 'react'
import { Beef, RefreshCw, Tag, WifiOff } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getPendingCount } from '@/lib/sync'
import MangaTab from '@/components/campo/MangaTab'
import AnimalesTab from '@/components/campo/AnimalesTab'
import SyncTab from '@/components/campo/SyncTab'

type Tab = 'manga' | 'animales' | 'sync'

const TABS: { id: Tab; label: string; icon: typeof Tag }[] = [
  { id: 'manga',    label: 'Manga',    icon: Tag },
  { id: 'animales', label: 'Animales', icon: Beef },
  { id: 'sync',     label: 'Sync',     icon: RefreshCw },
]

export default function Campo() {
  const [tab, setTab] = useState<Tab>('manga')
  const [pending, setPending] = useState(0)
  const [isOnline, setIsOnline] = useState(navigator.onLine)

  useEffect(() => {
    const on = () => setIsOnline(true)
    const off = () => setIsOnline(false)
    window.addEventListener('online', on)
    window.addEventListener('offline', off)
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off) }
  }, [])

  useEffect(() => {
    getPendingCount().then(setPending)
    const interval = setInterval(() => getPendingCount().then(setPending), 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex flex-col h-full bg-surface-900">
      {/* Header */}
      <div className="border-b border-surface-800 px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold text-white flex items-center gap-2">
              Campo / Manga
            </h1>
            <p className="text-xs text-slate-500">Modo offline · datos locales</p>
          </div>
          {!isOnline && (
            <div className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-900/30 border border-amber-800 px-2.5 py-1 rounded-full">
              <WifiOff size={11} />
              Offline
            </div>
          )}
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-surface-800 bg-surface-950">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 py-3 text-sm font-medium relative transition-colors',
              tab === id
                ? 'text-brand-400 border-b-2 border-brand-500 -mb-px'
                : 'text-slate-500 hover:text-slate-300'
            )}
          >
            <Icon size={14} />
            {label}
            {id === 'sync' && pending > 0 && (
              <span className="absolute top-2 right-[calc(50%-16px)] w-4 h-4 bg-amber-500 rounded-full text-[9px] font-bold text-white flex items-center justify-center">
                {pending > 9 ? '9+' : pending}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {tab === 'manga' && <MangaTab />}
        {tab === 'animales' && <AnimalesTab />}
        {tab === 'sync' && <SyncTab />}
      </div>
    </div>
  )
}
