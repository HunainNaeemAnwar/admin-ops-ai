"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { PayslipListResponse } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
import { Select } from "@/components/ui/select"
import { Avatar } from "@/components/ui/avatar"
import { FileText, Download, ChevronLeft, ChevronRight } from "lucide-react"

const now = new Date()
const currentYear = now.getFullYear()
const currentMonth = now.getMonth() + 1

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
]

function parsePayslipName(name: string) {
  const parts = name.split("_")
  return { worker: parts[0] || name, year: parts[1] || "", month: parts[2] || "" }
}

export default function PayslipsPage() {
  const [year, setYear] = useState(currentYear)
  const [month, setMonth] = useState(currentMonth)
  const [data, setData] = useState<PayslipListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchApi<PayslipListResponse>(
        `/admin/payslips?year=${year}&month=${month}`
      )
      setData(result)
    } catch {
      setError("Failed to load payslips")
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

  const allNames = [...new Set(data?.pdfs || [])]
  const allWorkers = allNames.map((n) => ({ key: n, ...parsePayslipName(n) }))

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold sm:text-2xl" style={{ color: "var(--color-foreground)" }}>
        Payslips
      </h1>

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
      </div>

      {!data || allWorkers.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <FileText size={40} style={{ color: "var(--color-muted-light)" }} />
          <p className="text-sm" style={{ color: "var(--color-muted)" }}>
            No payslips generated for this period.
          </p>
          <p className="text-xs" style={{ color: "var(--color-muted-light)" }}>
            Ask the AI chatbot to generate payslips.
          </p>
        </div>
      ) : (
        <Card>
          <div className="swipeable-scroll overflow-x-auto">
            <table className="min-w-full text-sm" style={{ borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid var(--color-border)" }}>
                  <th
                    className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider"
                    style={{ color: "var(--color-muted)" }}
                  >
                    Worker
                  </th>
                  <th
                    className="px-4 py-2.5 text-center text-xs font-semibold uppercase tracking-wider"
                    style={{ color: "var(--color-muted)" }}
                  >
                    PDF
                  </th>
                </tr>
              </thead>
              <tbody>
                {allWorkers.map((p, i) => {
                  const hasPdf = data.pdfs.includes(p.key)
                  return (
                    <tr
                      key={p.key}
                      style={{
                        borderBottom: "1px solid var(--color-border)",
                        background: i % 2 === 0 ? "var(--color-surface)" : "var(--color-table-stripe)",
                      }}
                      className="transition-colors hover:bg-surface-alt"
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <Avatar name={p.worker} size="sm" />
                          <span className="font-medium" style={{ color: "var(--color-foreground)" }}>{p.worker}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        {hasPdf ? (
                          <a
                            href={`/admin/payslip/pdf/${p.worker}/${p.year}/${p.month}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 rounded-md px-3 py-1 text-xs font-medium transition-colors"
                            style={{
                              background: "var(--color-accent)",
                              color: "var(--color-on-accent)",
                            }}
                          >
                            <Download size={14} />
                            PDF
                          </a>
                        ) : (
                          <span style={{ color: "var(--color-muted-light)" }}>-</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
