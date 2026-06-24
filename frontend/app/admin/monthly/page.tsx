"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { MonthlyReport } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
import { Select } from "@/components/ui/select"
import { Breadcrumbs } from "@/components/ui/breadcrumbs"
import { Avatar } from "@/components/ui/avatar"
import { Download, ChevronLeft, ChevronRight } from "lucide-react"

const now = new Date()
const currentYear = now.getFullYear()
const currentMonth = now.getMonth() + 1

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
]

export default function MonthlyReportPage() {
  const [year, setYear] = useState(currentYear)
  const [month, setMonth] = useState(currentMonth)
  const [data, setData] = useState<MonthlyReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchApi<MonthlyReport>(
        `/admin/monthly?year=${year}&month=${month}`
      )
      setData(result)
    } catch {
      setError("Failed to load monthly report")
    } finally {
      setLoading(false)
    }
  }, [year, month])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const prevMonth = () => {
    if (month === 1) { setMonth(12); setYear(y => y - 1) }
    else setMonth(m => m - 1)
  }

  const nextMonth = () => {
    if (month === 12) { setMonth(1); setYear(y => y + 1) }
    else setMonth(m => m + 1)
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

  const productCodes =
    data && data.workers.length > 0
      ? [...new Set(data.workers.flatMap((w) => Object.keys(w.totals)))]
      : []

  const grandTotals = productCodes.reduce((acc, code) => {
    acc[code] = data?.workers.reduce((sum, w) => sum + (w.totals[code] || 0), 0) || 0
    return acc
  }, {} as Record<string, number>)

  return (
    <div className="space-y-4">
      <Breadcrumbs />

      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold sm:text-2xl" style={{ color: "var(--color-foreground)" }}>
          Monthly Report
        </h1>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <button
          onClick={prevMonth}
          className="rounded-md border p-2 transition-colors hover:bg-surface-alt"
          style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
          aria-label="Previous month"
        >
          <ChevronLeft size={18} />
        </button>
        <Select
          label="Month"
          options={MONTHS.map((m, i) => ({ value: String(i + 1), label: m }))}
          value={String(month)}
          onChange={(e) => setMonth(Number(e.target.value))}
        />
        <div className="flex flex-col gap-1">
          <label className="text-xs font-medium" style={{ color: "var(--color-muted)" }}>Year</label>
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded-md border px-3 py-2 text-sm"
            style={{
              borderColor: "var(--color-border)",
              background: "var(--color-surface)",
              color: "var(--color-foreground)",
            }}
          />
        </div>
        <button
          onClick={nextMonth}
          className="rounded-md border p-2 transition-colors hover:bg-surface-alt"
          style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
          aria-label="Next month"
        >
          <ChevronRight size={18} />
        </button>
        <a
          href={`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/api/worker/Naeem/excel/${year}/${month}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-md bg-brand-green px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
        >
          <Download size={16} />
          Excel
        </a>
      </div>

      {!data || data.workers.length === 0 ? (
        <div className="py-8 text-center text-sm" style={{ color: "var(--color-muted)" }}>
          No data for this period.
        </div>
      ) : (
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
                  {productCodes.map((code) => (
                    <th
                      key={code}
                      className="whitespace-nowrap px-3 py-2.5 text-right text-xs font-semibold uppercase tracking-wider"
                      style={{ color: "var(--color-muted)" }}
                    >
                      {code}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.workers.map((w, i) => (
                  <tr
                    key={w.worker}
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
                      <Avatar name={w.worker} size="sm" />
                      <span style={{ color: "var(--color-foreground)" }}>{w.worker}</span>
                    </td>
                    {productCodes.map((code) => (
                      <td
                        key={code}
                        className="whitespace-nowrap px-3 py-2.5 text-right font-mono"
                        style={{ color: "var(--color-foreground)" }}
                      >
                        {w.totals[code] ? w.totals[code].toLocaleString() : (
                          <span style={{ color: "var(--color-muted-light)" }}>-</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
                {/* Grand Total Row */}
                <tr
                  className="font-semibold"
                  style={{ borderTop: "2px solid var(--color-border)", background: "var(--color-surface-alt)" }}
                >
                  <td
                    className="sticky left-0 z-10 px-3 py-2.5 font-bold"
                    style={{ color: "var(--color-foreground)", background: "var(--color-surface-alt)" }}
                  >
                    Total
                  </td>
                  {productCodes.map((code) => (
                    <td
                      key={code}
                      className="whitespace-nowrap px-3 py-2.5 text-right font-mono font-bold"
                      style={{ color: "var(--color-accent)" }}
                    >
                      {grandTotals[code].toLocaleString()}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
