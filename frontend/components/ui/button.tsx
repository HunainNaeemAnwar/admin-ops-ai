import type { ButtonHTMLAttributes, ReactNode } from "react"

type Variant = "primary" | "secondary" | "ghost" | "icon" | "danger" | "accent"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  children?: ReactNode
}

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center rounded-lg text-sm font-semibold transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none px-4 py-2.5 min-h-[44px] active:scale-[0.98]"

  const variantStyles: Record<Variant, React.CSSProperties> = {
    primary: { background: "var(--color-primary)", color: "var(--color-on-primary)" },
    accent: { background: "var(--color-accent)", color: "var(--color-on-accent)" },
    secondary: { background: "transparent", border: "1px solid var(--color-border)", color: "var(--color-foreground)" },
    ghost: { background: "transparent", color: "var(--color-foreground)" },
    icon: { background: "transparent", color: "var(--color-foreground)", padding: "8px", borderRadius: "9999px" },
    danger: { background: "var(--color-destructive)", color: "#FFFFFF" },
  }

  return (
    <button
      className={base}
      style={variantStyles[variant]}
      onMouseEnter={(e) => {
        if (variant === "primary") e.currentTarget.style.background = "var(--color-primary-hover)"
        else if (variant === "accent") e.currentTarget.style.background = "var(--color-accent-hover)"
        else if (variant === "danger") e.currentTarget.style.background = "var(--color-destructive-hover)"
        else if (variant === "secondary" || variant === "ghost" || variant === "icon") e.currentTarget.style.background = "var(--color-surface-alt)"
      }}
      onMouseLeave={(e) => {
        if (variant === "primary") e.currentTarget.style.background = "var(--color-primary)"
        else if (variant === "accent") e.currentTarget.style.background = "var(--color-accent)"
        else if (variant === "danger") e.currentTarget.style.background = "var(--color-destructive)"
        else if (variant === "secondary" || variant === "ghost" || variant === "icon") e.currentTarget.style.background = "transparent"
      }}
      {...props}
    >
      {children}
    </button>
  )
}
