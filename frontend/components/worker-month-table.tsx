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
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-4 py-8">
        <p className="text-red-600">{error}</p>
        <button
          className="rounded-md bg-brand-blue px-4 py-2 text-sm text-white hover:bg-blue-700"
          onClick={fetchData}
        >
          Retry
        </button>
      </div>
    )
  }

  if (!data || data.days.length === 0) {
    return (
      <p className="py-8 text-center text-gray-500">
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
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="whitespace-nowrap px-3 py-2 text-left font-medium text-gray-500">
              Date
            </th>
            {productCodes.map((code) => (
              <th
                key={code}
                className="whitespace-nowrap px-3 py-2 text-right font-medium text-gray-500"
              >
                {code}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {data.days.map((day) => {
            const isFuture = day.date > todayStr
            return (
              <tr key={day.date} className="hover:bg-gray-50">
                <td className="whitespace-nowrap px-3 py-2 text-gray-700">
                  {day.date}
                </td>
                {productCodes.map((code) => {
                  if (isFuture) {
                    return (
                      <td key={code} className="whitespace-nowrap px-3 py-2" />
                    )
                  }
                  return (
                    <td
                      key={code}
                      className="whitespace-nowrap px-3 py-2 text-right text-gray-700"
                    >
                      {day.status === "absent"
                        ? (day.reason || "ABSENT")
                        : (day.products[code] ?? "-")}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
        {hasAnyData && (
          <tfoot className="border-t-2 border-gray-300 bg-gray-50">
            <tr>
              <td className="whitespace-nowrap px-3 py-2 text-left font-semibold text-gray-900">
                Total
              </td>
              {productCodes.map((code) => (
                <td
                  key={code}
                  className="whitespace-nowrap px-3 py-2 text-right font-semibold text-gray-900"
                >
                  {productTotals[code]}
                </td>
              ))}
            </tr>
          </tfoot>
        )}
      </table>
    </div>
  )
}
