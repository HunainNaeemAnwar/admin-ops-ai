import type { ButtonHTMLAttributes, ReactNode } from "react"

type Variant = "primary" | "secondary" | "ghost" | "icon" | "danger"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  children?: ReactNode
}

const variantStyles: Record<Variant, string> = {
  primary: "bg-brand-green text-white hover:opacity-90",
  secondary: "border hover:bg-surface-alt",
  ghost: "hover:bg-surface-alt",
  icon: "hover:bg-surface-alt p-2 rounded-full",
  danger: "bg-brand-red text-white hover:opacity-90",
}

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center rounded-md text-sm font-medium transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none px-4 py-2 min-h-[44px]"

  const isBordered = variant === "secondary"
  const borderStyle = isBordered ? { borderColor: "var(--color-border)" } : undefined

  return (
    <button
      className={`${base} ${variantStyles[variant]} ${className}`}
      style={borderStyle}
      {...props}
    >
      {children}
    </button>
  )
}
