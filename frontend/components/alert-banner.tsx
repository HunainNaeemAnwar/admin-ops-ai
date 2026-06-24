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
    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm dark:border-red-900/50 dark:bg-red-950/50">
      <div className="flex items-start gap-3">
        <AlertTriangle size={18} className="mt-0.5 shrink-0 text-red-600 dark:text-red-400" />
        <div className="flex-1">
          <p className="font-medium text-red-800 dark:text-red-300">{message}</p>
          {details && details.length > 0 && (
            <p className="mt-1 text-red-600 dark:text-red-400">
              {details.join(", ")}
            </p>
          )}
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="shrink-0 rounded p-1 text-red-400 transition-colors hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/50"
          aria-label="Dismiss alert"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  )
}
