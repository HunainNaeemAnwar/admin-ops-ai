"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { MonthlyReport } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
import { Select } from "@/components/ui/select"
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
          className="rounded-lg bg-brand-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors shadow-sm"
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
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold sm:text-2xl" style={{ color: "var(--color-foreground)" }}>
          Monthly Report
        </h1>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex items-end gap-2">
          <button
            onClick={prevMonth}
            className="shrink-0 rounded-lg border-2 p-2.5 transition-colors"
            style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
            aria-label="Previous month"
          >
            <ChevronLeft size={18} />
          </button>
          <div className="flex-1 sm:w-auto">
            <Select
              label="Month"
              options={MONTHS.map((m, i) => ({ value: String(i + 1), label: m }))}
              value={String(month)}
              onChange={(e) => setMonth(Number(e.target.value))}
            />
          </div>
          <div className="flex flex-col gap-1.5 flex-1 sm:w-auto">
            <label className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--color-muted)" }}>Year</label>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="w-full rounded-lg border-2 px-3 py-2.5 text-sm font-medium transition-colors focus:outline-none"
              style={{
                borderColor: "var(--color-border)",
                background: "var(--color-surface)",
                color: "var(--color-foreground)",
              }}
            />
          </div>
          <button
            onClick={nextMonth}
            className="shrink-0 rounded-lg border-2 p-2.5 transition-colors"
            style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
            aria-label="Next month"
          >
            <ChevronRight size={18} />
          </button>
        </div>
        <a
          href={`/admin/monthly/excel?year=${year}&month=${month}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors"
          style={{ background: "var(--color-success)", color: "#FFFFFF" }}
        >
          <Download size={16} />
          Download Excel
        </a>
      </div>

      {!data || data.workers.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed py-12 text-center" style={{ borderColor: "var(--color-border)" }}>
          <p className="text-sm font-medium" style={{ color: "var(--color-muted)" }}>
            No data for this period.
          </p>
        </div>
      ) : (
        <Card>
          <div className="swipeable-scroll overflow-x-auto">
            <table className="min-w-full text-sm" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid var(--color-border)" }}>
                  <th
                    className="sticky left-0 z-10 px-4 py-3 text-left text-xs font-bold uppercase tracking-wider"
                    style={{ color: "var(--color-muted)", background: "var(--color-surface)" }}
                  >
                    Worker
                  </th>
                  {productCodes.map((code) => (
                    <th
                      key={code}
                      className="whitespace-nowrap px-4 py-3 text-right text-xs font-bold uppercase tracking-wider"
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
                      className="transition-colors"
                    >
                    <td
                      className="sticky left-0 z-10 flex items-center gap-3 whitespace-nowrap px-4 py-3 font-semibold"
                      style={{ background: i % 2 === 0 ? "var(--color-surface)" : "var(--color-table-stripe)" }}
                    >
                      <Avatar name={w.worker} size="sm" />
                      <span style={{ color: "var(--color-foreground)" }}>{w.worker}</span>
                    </td>
                    {productCodes.map((code) => (
                      <td
                        key={code}
                        className="whitespace-nowrap px-4 py-3 text-right font-mono font-semibold tabular-nums"
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
                  style={{ borderTop: "2px solid var(--color-border)", background: "var(--color-surface-alt)" }}
                >
                  <td
                    className="sticky left-0 z-10 px-4 py-3 font-bold"
                    style={{ color: "var(--color-foreground)", background: "var(--color-surface-alt)" }}
                  >
                    Total
                  </td>
                  {productCodes.map((code) => (
                    <td
                      key={code}
                      className="whitespace-nowrap px-4 py-3 text-right font-mono text-sm font-bold tabular-nums"
                      style={{ color: "var(--color-primary)" }}
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
