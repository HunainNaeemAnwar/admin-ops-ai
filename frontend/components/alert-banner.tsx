"use client"

import { AlertTriangle, X } from "lucide-react"
import { useState } from "react"

interface AlertBannerProps {
  message: string
  details?: string[]
}

export function AlertBanner({ message, details }: AlertBannerProps) {
  const [dismissed, setDismissed] = useState(false)

  if (dismissed) return null

  return (
    <div
      className="rounded-lg px-4 py-3 text-sm"
      style={{ background: "var(--color-destructive)", color: "#FFFFFF", opacity: 0.9 }}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle size={18} className="mt-0.5 shrink-0" />
        <div className="flex-1">
          <p className="font-medium">{message}</p>
          {details && details.length > 0 && (
            <p className="mt-1 opacity-90">
              {details.join(", ")}
            </p>
          )}
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="shrink-0 rounded p-1 opacity-70 transition-opacity hover:opacity-100"
          aria-label="Dismiss alert"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  )
}
