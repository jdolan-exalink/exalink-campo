interface SwitchProps {
  checked: boolean
  onChange: (v: boolean) => void
  label?: string
  size?: 'sm' | 'md'
  color?: 'brand' | 'field' | 'sky'
}

export default function Switch({ checked, onChange, label, size = 'md', color = 'brand' }: SwitchProps) {
  const dims = size === 'sm' ? { w: 'w-8', h: 'h-4', knob: 'w-3 h-3', on: 'translate-x-4', off: 'translate-x-0.5' }
    : { w: 'w-10', h: 'h-5', knob: 'w-4 h-4', on: 'translate-x-5', off: 'translate-x-0.5' }
  const colorOn = color === 'field' ? 'bg-field' : color === 'sky' ? 'bg-sky-500' : 'bg-brand-600'
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex items-center gap-2 focus:outline-none"
    >
      <span className={`${dims.w} ${dims.h} rounded-full transition-colors flex items-center ${checked ? colorOn : 'bg-surface-600'}`}>
        <span className={`${dims.knob} bg-white rounded-full shadow transition-transform ${checked ? dims.on : dims.off}`} />
      </span>
      {label && <span className="text-sm text-slate-300 select-none">{label}</span>}
    </button>
  )
}
