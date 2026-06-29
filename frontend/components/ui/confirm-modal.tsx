"use client"

import { useEffect, useState, useRef } from "react"
import { AlertTriangle, Trash2, X, Info } from "lucide-react"
import { Button } from "./button"

interface ConfirmModalProps {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  countdown?: number
  variant?: "danger" | "primary"
  onConfirm: () => void
  onCancel: () => void
  loading?: boolean
}

export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  countdown = 0,
  variant = "danger",
  onConfirm,
  onCancel,
  loading = false,
}: ConfirmModalProps) {
  const [count, setCount] = useState(countdown)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!open) {
      if (timerRef.current) clearInterval(timerRef.current)
      setCount(countdown)
      return
    }
    if (countdown <= 0) return
    timerRef.current = setInterval(() => {
      setCount((c) => {
        if (c <= 1) {
          if (timerRef.current) clearInterval(timerRef.current)
          return 0
        }
        return c - 1
      })
    }, 1000)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [open, countdown])

  useEffect(() => {
    if (!open) setCount(countdown)
  }, [open, countdown])

  if (!open) return null

  const canConfirm = count <= 0
  const isDanger = variant === "danger"

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0,0,0,0.55)", backdropFilter: "blur(6px)" }}
      onClick={onCancel}
    >
      <div
        className="w-full max-w-md rounded-2xl shadow-2xl"
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="flex items-center justify-between px-6 pt-5 pb-3"
          style={{
            borderBottom: "1px solid var(--color-border)",
          }}
        >
          <div className="flex items-center gap-3">
            <div
              className="flex items-center justify-center rounded-full"
              style={{
                width: 36,
                height: 36,
                background: isDanger
                  ? "color-mix(in srgb, var(--color-destructive) 15%, transparent)"
                  : "color-mix(in srgb, var(--color-primary) 15%, transparent)",
              }}
            >
              {isDanger ? (
                <Trash2 size={18} style={{ color: "var(--color-destructive)" }} />
              ) : (
                <Info size={18} style={{ color: "var(--color-primary)" }} />
              )}
            </div>
            <h3
              className="text-base font-bold"
              style={{ color: "var(--color-foreground)" }}
            >
              {title}
            </h3>
          </div>
          <button
            onClick={onCancel}
            className="flex items-center justify-center rounded-full transition-colors hover:opacity-70"
            style={{
              width: 28,
              height: 28,
              color: "var(--color-muted)",
              background: "var(--color-surface-alt)",
            }}
          >
            <X size={16} />
          </button>
        </div>

        <div className="px-6 py-4">
          <p
            className="text-sm leading-relaxed"
            style={{ color: "var(--color-muted)" }}
          >
            {message}
          </p>

          {count > 0 && (
            <div className="mt-5 flex flex-col items-center gap-2">
              <div
                className="flex items-center justify-center rounded-full text-xl font-bold tabular-nums"
                style={{
                  width: 52,
                  height: 52,
                  background: isDanger
                    ? "color-mix(in srgb, var(--color-destructive) 10%, transparent)"
                    : "color-mix(in srgb, var(--color-primary) 10%, transparent)",
                  color: isDanger
                    ? "var(--color-destructive)"
                    : "var(--color-primary)",
                  border: `2px solid ${isDanger ? "var(--color-destructive)" : "var(--color-primary)"}`,
                }}
              >
                {count}
              </div>
              <p
                className="text-xs font-medium"
                style={{ color: "var(--color-muted)" }}
              >
                Please wait before confirming...
              </p>
            </div>
          )}

          {loading && (
            <div className="mt-5 flex items-center justify-center gap-2">
              <span
                className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-t-transparent"
                style={{
                  borderColor: "var(--color-muted)",
                  borderTopColor: "transparent",
                }}
              />
              <span className="text-sm" style={{ color: "var(--color-muted)" }}>
                Deleting...
              </span>
            </div>
          )}

          {count <= 0 && !loading && (
            <div className="mt-2 flex items-start gap-2 rounded-lg px-3 py-2"
              style={{
                background: isDanger
                  ? "color-mix(in srgb, var(--color-destructive) 8%, transparent)"
                  : "color-mix(in srgb, var(--color-primary) 8%, transparent)",
              }}
            >
              <AlertTriangle
                size={14}
                className="mt-0.5 shrink-0"
                style={{ color: isDanger ? "var(--color-destructive)" : "var(--color-primary)" }}
              />
              <p
                className="text-xs"
                style={{ color: isDanger ? "var(--color-destructive)" : "var(--color-primary)" }}
              >
                {isDanger
                  ? "This action cannot be undone. All data for this date will be permanently deleted."
                  : "Are you sure you want to proceed with this action?"}
              </p>
            </div>
          )}
        </div>

        <div
          className="flex items-center justify-end gap-3 px-6 py-4"
          style={{
            borderTop: "1px solid var(--color-border)",
          }}
        >
          <Button variant="secondary" onClick={onCancel} disabled={loading}>
            {cancelLabel}
          </Button>
          <Button
            variant={variant}
            onClick={onConfirm}
            disabled={!canConfirm || loading}
          >
            {canConfirm ? confirmLabel : `${confirmLabel} (${count}s)`}
          </Button>
        </div>
      </div>
    </div>
  )
}
