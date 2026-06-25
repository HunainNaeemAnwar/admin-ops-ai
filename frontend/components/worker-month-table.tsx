"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { WorkerMonthData, Product } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"

interface Props {
  workerName: string
  year: number
  month: number
  products: Product[]
  refreshKey?: number
}

export function WorkerMonthTable({ workerName, year, month, products, refreshKey = 0 }: Props) {
  const [data, setData] = useState<WorkerMonthData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchApi<WorkerMonthData>(
        `/api/worker/${encodeURIComponent(workerName)}/month/${year}/${month}`
      )
      setData(result)
    } catch {
      setError("Failed to load data")
    } finally {
      setLoading(false)
    }
  }, [workerName, year, month, refreshKey])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  if (loading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-4 py-8">
        <p style={{ color: "var(--color-destructive)" }}>{error}</p>
        <button
          className="rounded-md px-4 py-2 text-sm font-medium text-white transition-opacity"
          style={{ background: "var(--color-success)" }}
          onClick={fetchData}
        >
          Retry
        </button>
      </div>
    )
  }

  if (!data || data.days.length === 0) {
    return (
      <p className="py-8 text-center text-sm" style={{ color: "var(--color-muted)" }}>
        No data for this period
      </p>
    )
  }

  const productCodes = products.map((p) => p.code)
  const today = new Date()
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`

  const presentDays = data.days.filter((d) => d.status === "present")
  const productTotals: Record<string, number> = {}
  for (const code of productCodes) {
    productTotals[code] = presentDays.reduce(
      (sum, d) => sum + (d.products[code] ?? 0), 0
    )
  }
  const hasAnyData = presentDays.length > 0

  return (
    <div className="rounded-lg border" style={{ borderColor: "var(--color-border)" }}>
      <div className="swipeable-scroll overflow-x-auto">
        <table className="w-full text-xs sm:text-sm" style={{ borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid var(--color-border)", background: "var(--color-surface-alt)" }}>
              <th
                className="sticky left-0 z-10 whitespace-nowrap px-1.5 py-2 text-left text-[10px] font-semibold uppercase tracking-wider sm:px-3 sm:py-2.5 sm:text-xs"
                style={{ color: "var(--color-muted)", background: "var(--color-surface-alt)" }}
              >
                Date
              </th>
              {productCodes.map((code) => (
                <th
                  key={code}
                  className="whitespace-nowrap px-1.5 py-2 text-right text-[10px] font-semibold uppercase tracking-wider sm:px-3 sm:py-2.5 sm:text-xs"
                  style={{ color: "var(--color-muted)" }}
                >
                  {code}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.days.map((day, i) => {
              const isFuture = day.date > todayStr
              const isToday = day.date === todayStr
              const shortDate = day.date.slice(5)
              return (
                <tr
                  key={day.date}
                  style={{
                    borderBottom: "1px solid var(--color-border)",
                    background: isToday
                      ? "rgba(37, 99, 235, 0.05)"
                      : i % 2 === 0 ? "var(--color-surface)" : "var(--color-table-stripe)",
                  }}
                >
                  <td
                    className="sticky left-0 z-10 whitespace-nowrap px-1.5 py-2 text-[11px] font-medium sm:px-3 sm:py-2.5 sm:text-xs"
                    style={{
                      color: "var(--color-foreground)",
                      background: isToday
                        ? "rgba(37, 99, 235, 0.05)"
                        : i % 2 === 0 ? "var(--color-surface)" : "var(--color-table-stripe)",
                    }}
                  >
                    <span className="hidden sm:inline">{day.date}</span>
                    <span className="sm:hidden">{shortDate}</span>
                  </td>
                  {productCodes.map((code) => {
                    if (isFuture) {
                      return <td key={code} className="whitespace-nowrap px-1.5 py-2 sm:px-3 sm:py-2.5" />
                    }
                    if (day.status === "absent") {
                      return (
                        <td
                          key={code}
                          className="whitespace-nowrap px-1.5 py-2 text-right sm:px-3 sm:py-2.5"
                        >
                          <span
                            className="inline-block rounded px-1 py-0.5 text-[10px] font-medium sm:text-xs"
                            style={{
                              background: "rgba(220, 38, 38, 0.1)",
                              color: "var(--color-destructive)",
                            }}
                          >
                            ABSENT
                          </span>
                        </td>
                      )
                    }
                    return (
                      <td
                        key={code}
                        className="whitespace-nowrap px-1.5 py-2 text-right font-mono text-[11px] sm:px-3 sm:py-2.5 sm:text-sm"
                        style={{ color: "var(--color-foreground)" }}
                      >
                        {day.products[code] ?? (
                          <span style={{ color: "var(--color-muted-light)" }}>-</span>
                        )}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
          {hasAnyData && (
            <tfoot>
              <tr style={{ borderTop: "2px solid var(--color-border)", background: "var(--color-surface-alt)" }}>
                <td
                  className="sticky left-0 z-10 whitespace-nowrap px-1.5 py-2 text-left text-[10px] font-bold uppercase tracking-wider sm:px-3 sm:py-2.5 sm:text-xs"
                  style={{ color: "var(--color-foreground)", background: "var(--color-surface-alt)" }}
                >
                  Total
                </td>
                {productCodes.map((code) => (
                  <td
                    key={code}
                    className="whitespace-nowrap px-1.5 py-2 text-right font-mono text-[11px] font-bold sm:px-3 sm:py-2.5 sm:text-sm"
                    style={{ color: "var(--color-accent)" }}
                  >
                    {productTotals[code].toLocaleString()}
                  </td>
                ))}
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </div>
  )
}
