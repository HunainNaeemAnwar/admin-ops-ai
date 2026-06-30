"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { DailyReport } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Users, Package, AlertTriangle, UserCheck, UserX } from "lucide-react"

const WORKERS = ["Naeem", "Kaleem", "Akbar", "Suny", "Sajjad", "Irfan", "Kashif", "Gulmast"]

const productVar: Record<string, string> = {
  NUT: "var(--color-product-nut)",
  "10*20": "var(--color-product-10x20)",
  "6*25": "var(--color-product-6x25)",
  "6*30": "var(--color-product-6x30)",
  "10*25": "var(--color-product-10x25)",
}

export default function AdminOverviewPage() {
  const [data, setData] = useState<DailyReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchApi<DailyReport>("/admin/daily")
      setData(result)
    } catch {
      setError("Failed to load today's data")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  if (loading) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-7 w-48" />
        <div className="grid grid-cols-3 gap-4">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-56 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-20">
        <p className="text-sm font-medium" style={{ color: "var(--color-destructive)" }}>{error}</p>
        <button
          className="rounded-lg px-5 py-2.5 text-sm font-semibold transition-all hover:opacity-90 active:scale-[0.98]"
          style={{ background: "var(--color-primary)", color: "var(--color-on-primary)" }}
          onClick={fetchData}
        >
          Retry
        </button>
      </div>
    )
  }

  const presentWorkers = data
    ? new Set(data.entries.filter((e) => e.status === "present").map((e) => e.worker_name))
    : new Set<string>()
  const workersPresent = presentWorkers.size
  const absentWorkers = data
    ? new Set(data.entries.filter((e) => e.status === "absent").map((e) => e.worker_name))
    : new Set<string>()
  const totalAccounted = data ? new Set(data.entries.map((e) => e.worker_name)) : new Set<string>()
  const missingWorkers = WORKERS.filter((w) => !totalAccounted.has(w))

  const products = Object.entries(data?.totals || {})
  const hasAbsences = absentWorkers.size > 0 || missingWorkers.length > 0

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex items-end justify-between">
        <h1 className="text-xl font-bold" style={{ color: "var(--color-foreground)" }}>Dashboard</h1>
        <span className="text-xs tabular-nums" style={{ color: "var(--color-muted)" }}>{data?.date}</span>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="stat-card">
          <div className="flex items-center gap-2 mb-2">
            <span style={{ color: "var(--color-muted)" }}><UserCheck size={15} /></span>
            <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-secondary)" }}>Present</span>
          </div>
          <p className="text-2xl font-bold tabular-nums" style={{ color: "var(--color-foreground)" }}>
            {workersPresent}
            <span className="text-sm font-normal ml-1" style={{ color: "var(--color-muted)" }}>/ {WORKERS.length}</span>
          </p>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-2 mb-2">
            <span style={{ color: "var(--color-muted)" }}><Package size={15} /></span>
            <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--color-secondary)" }}>Products</span>
          </div>
          <p className="text-2xl font-bold tabular-nums" style={{ color: "var(--color-foreground)" }}>{products.length}</p>
        </div>

        <div className="stat-card">
          <div className="flex items-center gap-2 mb-2">
            <span style={{ color: hasAbsences ? "var(--color-destructive)" : "var(--color-muted)" }}>
              <UserX size={15} />
            </span>
            <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: hasAbsences ? "var(--color-destructive)" : "var(--color-secondary)" }}>
              Absent
            </span>
          </div>
          <p className="text-2xl font-bold tabular-nums" style={{ color: hasAbsences ? "var(--color-destructive)" : "var(--color-foreground)" }}>
            {absentWorkers.size}
            {missingWorkers.length > 0 && (
              <span className="text-sm font-normal ml-1" style={{ color: "var(--color-muted)" }}>
                +{missingWorkers.length}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Product Grid */}
      {products.length > 0 && (
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: "var(--color-secondary)" }}>
            Today&apos;s Production
          </h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {products.map(([product, qty]) => {
              const accent = productVar[product] || "var(--color-muted)"
              return (
                <div
                  key={product}
                  className="product-card"
                  style={{ "--product-accent": accent } as React.CSSProperties}
                >
                  <p className="text-[11px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: "var(--color-secondary)" }}>
                    {product}
                  </p>
                  <p className="text-2xl font-bold tabular-nums" style={{ color: accent }}>
                    {(qty as number).toLocaleString()}
                  </p>
                </div>
              )
            })}
          </div>
        </section>
      )}

      {/* Absent Workers */}
      {absentWorkers.size > 0 && (
        <section className="danger-card">
          <div className="flex items-center gap-2 mb-3">
            <UserX size={14} style={{ color: "var(--color-destructive)" }} />
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--color-destructive)" }}>
              On leave today
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {[...absentWorkers].map((w) => (
              <span
                key={w}
                className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium"
                style={{
                  background: "color-mix(in srgb, var(--color-destructive) 12%, var(--color-surface))",
                  color: "var(--color-destructive)",
                }}
              >
                {w}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Missing Workers */}
      {missingWorkers.length > 0 && (
        <section className="danger-card">
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle size={14} style={{ color: "var(--color-destructive)" }} />
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--color-destructive)" }}>
              Missing today — no entry
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {missingWorkers.map((w) => (
              <span
                key={w}
                className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium"
                style={{
                  background: "color-mix(in srgb, var(--color-destructive) 12%, var(--color-surface))",
                  color: "var(--color-destructive)",
                }}
              >
                {w}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Empty State */}
      {(!data || data.entries.length === 0) && (
        <div
          className="flex flex-col items-center justify-center rounded-xl py-16 text-center"
          style={{ border: "1px dashed var(--color-border-strong)" }}
        >
          <Package size={36} className="mb-3" style={{ color: "var(--color-muted-light)" }} />
          <p className="text-sm font-medium" style={{ color: "var(--color-muted)" }}>
            No production data for today.
          </p>
        </div>
      )}
    </div>
  )
}
