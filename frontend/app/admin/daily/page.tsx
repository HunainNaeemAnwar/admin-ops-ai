"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { DailyReport } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Breadcrumbs } from "@/components/ui/breadcrumbs"
import { Avatar } from "@/components/ui/avatar"
import { Calendar } from "lucide-react"

export default function DailyReportPage() {
  const [dateStr, setDateStr] = useState(() => {
    const now = new Date()
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`
  })
  const [data, setData] = useState<DailyReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [y, m, d] = dateStr.split("-").map(Number)
      const result = await fetchApi<DailyReport>(
        `/admin/daily?year=${y}&month=${m}&day=${d}`
      )
      setData(result)
    } catch {
      setError("Failed to load daily report")
    } finally {
      setLoading(false)
    }
  }, [dateStr])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const goToToday = () => {
    const now = new Date()
    setDateStr(
      `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`
    )
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
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

  const workers = [...new Set(data?.entries.map((e) => e.worker_name) || [])]
  const products = [...new Set(data?.entries.map((e) => e.product_code) || [])]

  const getQty = (worker: string, product: string) => {
    const entry = data?.entries.find(
      (e) => e.worker_name === worker && e.product_code === product
    )
    return entry?.quantity ?? null
  }

  return (
    <div className="space-y-4">
      <Breadcrumbs />

      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold sm:text-2xl" style={{ color: "var(--color-foreground)" }}>
          Daily Report
        </h1>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium" style={{ color: "var(--color-muted)" }}>
            Date
          </label>
          <input
            type="date"
            value={dateStr}
            onChange={(e) => setDateStr(e.target.value)}
            className="rounded-md border px-3 py-2 text-sm"
            style={{
              borderColor: "var(--color-border)",
              background: "var(--color-surface)",
              color: "var(--color-foreground)",
            }}
          />
        </div>
        <button
          onClick={goToToday}
          className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium transition-colors hover:bg-surface-alt"
          style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
        >
          <Calendar size={14} />
          Today
        </button>
      </div>

      {!data || data.entries.length === 0 ? (
        <div className="py-8 text-center text-sm" style={{ color: "var(--color-muted)" }}>
          No data for this date.
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2">
            <Badge variant="info">Workers: {workers.length}</Badge>
            <Badge>{data.total_pieces.toLocaleString()} pieces</Badge>
          </div>

          <Card>
            <div className="swipeable-scroll overflow-x-auto">
              <table className="min-w-full text-sm" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid var(--color-border)" }}>
                    <th
                      className="sticky left-0 z-10 px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wider"
                      style={{ color: "var(--color-muted)", background: "var(--color-surface)" }}
                    >
                      Worker
                    </th>
                    {products.map((p) => (
                      <th
                        key={p}
                        className="whitespace-nowrap px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wider"
                        style={{ color: "var(--color-muted)" }}
                      >
                        {p}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {workers.map((worker, i) => (
                    <tr
                      key={worker}
                      style={{
                        borderBottom: "1px solid var(--color-border)",
                        background: i % 2 === 0 ? "var(--color-surface)" : "var(--color-table-stripe)",
                      }}
                      className="transition-colors hover:bg-surface-alt"
                    >
                      <td
                        className="sticky left-0 z-10 flex items-center gap-2 whitespace-nowrap px-3 py-2.5 font-medium"
                        style={{ background: i % 2 === 0 ? "var(--color-surface)" : "var(--color-table-stripe)" }}
                      >
                        <Avatar name={worker} size="sm" />
                        <span style={{ color: "var(--color-foreground)" }}>{worker}</span>
                      </td>
                      {products.map((p) => {
                        const qty = getQty(worker, p)
                        return (
                          <td
                            key={p}
                            className="whitespace-nowrap px-3 py-2.5 text-right font-mono"
                            style={{ color: "var(--color-foreground)" }}
                          >
                            {qty !== null ? qty.toLocaleString() : (
                              <span style={{ color: "var(--color-muted-light)" }}>-</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
