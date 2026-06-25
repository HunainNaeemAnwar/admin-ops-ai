"use client"

import { useEffect, useState } from "react"
import { CheckCircle, XCircle, Info, X } from "lucide-react"

interface ToastProps {
  message: string
  type: "success" | "error" | "info"
  onDismiss: () => void
}

const icons = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
}

const bgColors: Record<string, React.CSSProperties> = {
  success: { background: "var(--color-toast-success)" },
  error: { background: "var(--color-toast-error)" },
  info: { background: "var(--color-toast-info)" },
}

export function Toast({ message, type, onDismiss }: ToastProps) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    requestAnimationFrame(() => setVisible(true))
    const timeout = setTimeout(() => {
      setVisible(false)
      setTimeout(onDismiss, 300)
    }, 3500)
    return () => clearTimeout(timeout)
  }, [onDismiss])

  const Icon = icons[type]

  return (
    <div
      role="alert"
      aria-live="polite"
      className="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-semibold text-white shadow-lg transition-all duration-300"
      style={{
        ...bgColors[type],
        transform: visible ? "translateX(0)" : "translateX(16px)",
        opacity: visible ? 1 : 0,
      }}
    >
      <Icon size={18} className="shrink-0" />
      <span className="flex-1">{message}</span>
      <button
        onClick={() => {
          setVisible(false)
          setTimeout(onDismiss, 300)
        }}
        className="shrink-0 rounded-lg p-1 opacity-70 transition-opacity hover:opacity-100"
        aria-label="Dismiss"
      >
        <X size={14} />
      </button>
    </div>
  )
}
