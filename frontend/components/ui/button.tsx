import type { ButtonHTMLAttributes, ReactNode } from "react"

type Variant = "primary" | "secondary" | "ghost" | "icon"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  children?: ReactNode
}

const variantStyles: Record<Variant, string> = {
  primary:
    "bg-brand-blue text-white hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
  secondary:
    "bg-gray-200 text-gray-800 hover:bg-gray-300 focus:ring-2 focus:ring-gray-400 focus:ring-offset-2",
  ghost:
    "bg-transparent text-gray-600 hover:bg-gray-100",
  icon:
    "bg-transparent text-gray-600 hover:bg-gray-100 p-2 rounded-full",
}

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonProps) {
  const base = "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none px-4 py-2"
  return (
    <button
      className={`${base} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
