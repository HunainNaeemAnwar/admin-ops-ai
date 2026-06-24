import type { ReactNode } from "react"

interface CardProps {
  title?: string
  children: ReactNode
  className?: string
}

export function Card({ title, children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-lg border p-4 sm:p-6 shadow-sm sm:shadow-md ${className}`}
      style={{
        background: "var(--color-surface)",
        borderColor: "var(--color-border)",
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
