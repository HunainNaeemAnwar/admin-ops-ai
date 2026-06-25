import type { ReactNode } from "react"

interface CardProps {
  title?: string
  children: ReactNode
  className?: string
  hover?: boolean
}

export function Card({ title, children, className = "", hover = false }: CardProps) {
  return (
    <div
      className={`rounded-xl border p-4 sm:p-6 ${hover ? "card-hover" : ""} ${className}`}
      style={{
        background: "var(--color-surface)",
        borderColor: "var(--color-border)",
        boxShadow: "var(--shadow-card)",
      }}
    >
      {title && (
        <h2
          className="mb-4 text-base font-semibold"
          style={{ color: "var(--color-foreground)" }}
        >
          {title}
        </h2>
      )}
      {children}
    </div>
  )
}
