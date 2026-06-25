interface ProgressBarProps {
  value: number
  max?: number
  className?: string
  showLabel?: boolean
}

export function ProgressBar({ value, max = 100, className = "", showLabel = false }: ProgressBarProps) {
  const pct = Math.min(Math.round((value / max) * 100), 100)

  return (
    <div className={className}>
      {showLabel && (
        <div className="mb-1.5 flex items-center justify-between text-xs font-semibold" style={{ color: "var(--color-muted)" }}>
          <span>{pct}% complete</span>
        </div>
      )}
      <div className="h-2.5 w-full overflow-hidden rounded-full" style={{ background: "var(--color-surface-alt)" }}>
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${pct}%`, background: "var(--color-primary)" }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        />
      </div>
    </div>
  )
}
