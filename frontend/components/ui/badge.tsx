import type { ReactNode } from "react"

type Variant = "default" | "success" | "danger" | "warning" | "info" | "accent"

interface BadgeProps {
  variant?: Variant
  children: ReactNode
  className?: string
}

const variantStyles: Record<Variant, React.CSSProperties> = {
  default: { background: "var(--color-surface-alt)", color: "var(--color-muted)" },
  success: { background: "var(--color-success)", color: "#FFFFFF" },
  danger: { background: "var(--color-destructive)", color: "#FFFFFF" },
  warning: { background: "var(--color-accent)", color: "var(--color-on-accent)" },
  info: { background: "var(--color-primary)", color: "var(--color-on-primary)" },
  accent: { background: "var(--color-accent)", color: "var(--color-on-accent)" },
}

export function Badge({ variant = "default", children, className = "" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${className}`}
      style={variantStyles[variant]}
    >
      {children}
    </span>
  )
}
