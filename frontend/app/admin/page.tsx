"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { DailyReport } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ProgressBar } from "@/components/ui/progress-bar"
import { AlertBanner } from "@/components/alert-banner"
import { Breadcrumbs } from "@/components/ui/breadcrumbs"
import { Users, Package, TrendingUp } from "lucide-react"

const WORKERS = ["Naeem", "Kaleem", "Akbar", "Suny", "Sajjad", "Irfan", "Kashif", "Gulmast"]

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month, 0).getDate()
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

  useEffect(() => {
    fetchData()
  }, [fetchData])

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
        <Skeleton className="h-48 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-4 py-12">
        <p style={{ color: "var(--color-destructive)" }}>{error}</p>
        <button
          className="rounded-md bg-brand-green px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
          onClick={fetchData}
        >
          Retry
        </button>
      </div>
    )
  }

  const workersPresent = data
    ? new Set(data.entries.map((e) => e.worker_name)).size
    : 0
  const missingWorkers = WORKERS.filter(
    (w) => !data?.entries.some((e) => e.worker_name === w)
  )

  const now = new Date()
  const daysInMonth = getDaysInMonth(now.getFullYear(), now.getMonth() + 1)
  const monthProgress = Math.round((now.getDate() / daysInMonth) * 100)

  const products = Object.entries(data?.totals || {})

  return (
    <div className="space-y-4">
      <Breadcrumbs />

      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold sm:text-2xl" style={{ color: "var(--color-foreground)" }}>
          Overview
        </h1>
        <Badge variant="info">{data?.date}</Badge>
      </div>

      {missingWorkers.length > 0 && (
        <AlertBanner
          message="Data not entered today for:"
          details={missingWorkers}
        />
      )}

      <div className="mb-2">
        <div className="flex items-center justify-between text-xs" style={{ color: "var(--color-muted)" }}>
          <span>Month Progress</span>
          <span>{now.getDate()}/{daysInMonth}</span>
        </div>
        <ProgressBar value={now.getDate()} max={daysInMonth} showLabel />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-green/10 text-brand-green">
              <Users size={20} />
            </div>
            <div>
              <p className="text-xs" style={{ color: "var(--color-muted)" }}>Workers</p>
              <p className="text-2xl font-bold" style={{ color: "var(--color-foreground)" }}>
                {workersPresent}
                <span className="text-sm font-normal" style={{ color: "var(--color-muted)" }}>/{WORKERS.length}</span>
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-green/10 text-brand-green">
              <Package size={20} />
            </div>
            <div>
              <p className="text-xs" style={{ color: "var(--color-muted)" }}>Total Pieces</p>
              <p className="text-2xl font-bold" style={{ color: "var(--color-foreground)" }}>
                {data?.total_pieces ?? 0}
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-green/10 text-brand-green">
              <TrendingUp size={20} />
            </div>
            <div>
              <p className="text-xs" style={{ color: "var(--color-muted)" }}>Products</p>
              <p className="text-2xl font-bold" style={{ color: "var(--color-foreground)" }}>
                {products.length}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {products.length > 0 && (
        <Card title="Per-Product Breakdown">
          <div className="space-y-3">
            {products.map(([product, qty]) => {
              const maxQty = Math.max(...products.map(([, q]) => q as number), 1)
              const pct = Math.round(((qty as number) / maxQty) * 100)
              return (
                <div key={product} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium" style={{ color: "var(--color-foreground)" }}>{product}</span>
                    <span className="font-mono font-semibold" style={{ color: "var(--color-foreground)" }}>
                      {(qty as number).toLocaleString()}
                    </span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full" style={{ background: "var(--color-surface-alt)" }}>
                    <div
                      className="h-full rounded-full bg-brand-green transition-all duration-700 ease-out"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {!data || data.entries.length === 0 ? (
        <div className="py-8 text-center text-sm" style={{ color: "var(--color-muted)" }}>
          No production data for today.
        </div>
      ) : null}
    </div>
  )
}
