"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { DailyReport } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { useTheme } from "@/lib/theme-context"
import { Users, Package, AlertTriangle } from "lucide-react"

const WORKERS = ["Naeem", "Kaleem", "Akbar", "Suny", "Sajjad", "Irfan", "Kashif", "Gulmast"]

const productAccents: Record<string, { light: string; dark: string }> = {
  NUT:      { light: "#2563EB", dark: "#60AFAA" },
  "10*20":  { light: "#D97706", dark: "#FBBF24" },
  "6*25":   { light: "#059669", dark: "#34D399" },
  "6*30":   { light: "#7C3AED", dark: "#A78BFA" },
  "10*25":  { light: "#DC2626", dark: "#F87171" },
}

export default function AdminOverviewPage() {
  const { theme } = useTheme()
  const dark = theme === "dark"

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

  useEffect(() => {
    fetchData()
  }, [fetchData])

  // Theme tokens
  const bg = dark ? "#111318" : "#F3F4F6"
  const card = dark ? "#181B22" : "#FFFFFF"
  const border = dark ? "#262A33" : "#E5E7EB"
  const text = dark ? "#E8EAED" : "#111827"
  const muted = dark ? "#6B7280" : "#9CA3AF"
  const statBg = dark ? "#181B22" : "#FFFFFF"
  const dangerBg = dark ? "#1C1517" : "#FEF2F2"
  const dangerBorder = dark ? "#3B2024" : "#FECACA"
  const dangerTag = dark ? "#2A1A1C" : "#FEE2E2"
  const dangerTagText = dark ? "#FCA5A5" : "#DC2626"
  const emptyBorder = dark ? "#262A33" : "#D1D5DB"
  const emptyIcon = dark ? "#374151" : "#D1D5DB"
  const missingTagBg = dark ? "#2A1A1C" : "#FEF2F2"
  const missingTagText = dark ? "#FCA5A5" : "#DC2626"

  if (loading) {
    return (
      <div style={{ background: bg, minHeight: "100vh", borderRadius: "12px", padding: "16px" }} className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-3 gap-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ background: bg, minHeight: "80vh" }} className="flex flex-col items-center justify-center gap-4">
        <p className="text-sm" style={{ color: "#DC2626" }}>{error}</p>
        <button
          className="rounded-lg px-5 py-2.5 text-sm font-semibold transition-opacity hover:opacity-90"
          style={{ background: "#2563EB", color: "#FFF" }}
          onClick={fetchData}
        >
          Retry
        </button>
      </div>
    )
  }

  const workersPresent = data
    ? new Set(data.entries.filter((e) => e.status === "present").map((e) => e.worker_name)).size
    : 0
  const absentWorkers = data
    ? new Set(data.entries.filter((e) => e.status === "absent").map((e) => e.worker_name)).size
    : 0
  const missingWorkers = WORKERS.filter(
    (w) => !data?.entries.some((e) => e.worker_name === w)
  )

  const products = Object.entries(data?.totals || {})

  return (
    <div style={{ background: bg, minHeight: "100vh", borderRadius: "12px", padding: "16px" }} className="space-y-5">

      {/* Header */}
      <div className="flex items-end justify-between">
        <h1 className="text-xl font-bold" style={{ color: text }}>Dashboard</h1>
        <span className="text-xs tabular-nums" style={{ color: muted }}>{data?.date}</span>
      </div>

      {/* Stat Row */}
      <div className="grid grid-cols-3 gap-3">
        <div style={{ background: statBg, border: `1px solid ${border}` }} className="rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <Users size={14} style={{ color: muted }} />
            <span className="text-[11px] font-medium uppercase tracking-wide" style={{ color: muted }}>Workers</span>
          </div>
          <p className="text-2xl font-bold tabular-nums" style={{ color: text }}>
            {workersPresent}<span className="text-sm font-normal" style={{ color: muted }}>/{WORKERS.length}</span>
          </p>
        </div>

        <div style={{ background: statBg, border: `1px solid ${border}` }} className="rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <Package size={14} style={{ color: muted }} />
            <span className="text-[11px] font-medium uppercase tracking-wide" style={{ color: muted }}>Products</span>
          </div>
          <p className="text-2xl font-bold tabular-nums" style={{ color: text }}>{products.length}</p>
        </div>

        <div style={{ background: statBg, border: `1px solid ${border}` }} className="rounded-xl px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle size={14} style={{ color: absentWorkers + missingWorkers.length > 0 ? "#DC2626" : muted }} />
            <span className="text-[11px] font-medium uppercase tracking-wide" style={{ color: muted }}>Absent</span>
          </div>
          <p className="text-2xl font-bold tabular-nums" style={{ color: absentWorkers + missingWorkers.length > 0 ? "#DC2626" : text }}>
            {absentWorkers}
            {missingWorkers.length > 0 && <span className="text-sm font-normal" style={{ color: muted }}> +{missingWorkers.length}</span>}
          </p>
        </div>
      </div>

      {/* Product Grid */}
      {products.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider mb-3" style={{ color: muted }}>
            Today&apos;s Production
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
            {products.map(([product, qty]) => {
              const accent = productAccents[product]?.[dark ? "dark" : "light"] || muted
              return (
                <div
                  key={product}
                  className="rounded-xl px-4 py-3"
                  style={{ background: card, border: `1px solid ${border}` }}
                >
                  <p className="text-[11px] font-medium mb-1" style={{ color: muted }}>{product}</p>
                  <p className="text-xl font-bold tabular-nums" style={{ color: accent }}>
                    {(qty as number).toLocaleString()}
                  </p>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Absent Workers */}
      {absentWorkers > 0 && (
        <div
          className="rounded-xl px-4 py-3"
          style={{ background: dangerBg, border: `1px solid ${dangerBorder}` }}
        >
          <p className="text-xs font-semibold mb-2" style={{ color: "#DC2626" }}>
            On leave today
          </p>
          <div className="flex flex-wrap gap-1.5">
            {[...new Set(data?.entries.filter((e) => e.status === "absent").map((e) => e.worker_name))].map((w) => (
              <span
                key={w}
                className="rounded-md px-2.5 py-1 text-xs font-medium"
                style={{ background: missingTagBg, color: missingTagText }}
              >
                {w}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Missing Workers */}
      {missingWorkers.length > 0 && (
        <div
          className="rounded-xl px-4 py-3"
          style={{ background: dangerBg, border: `1px solid ${dangerBorder}` }}
        >
          <p className="text-xs font-semibold mb-2" style={{ color: "#DC2626" }}>Missing today</p>
          <div className="flex flex-wrap gap-1.5">
            {missingWorkers.map((w) => (
              <span
                key={w}
                className="rounded-md px-2.5 py-1 text-xs font-medium"
                style={{ background: missingTagBg, color: missingTagText }}
              >
                {w}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Empty */}
      {!data || data.entries.length === 0 ? (
        <div className="rounded-xl py-12 text-center" style={{ border: `1px dashed ${emptyBorder}` }}>
          <Package size={32} className="mx-auto mb-2" style={{ color: emptyIcon }} />
          <p className="text-sm" style={{ color: muted }}>No production data for today.</p>
        </div>
      ) : null}
    </div>
  )
}
