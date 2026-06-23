"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { DailyReport } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"

const now = new Date()
const y = now.getFullYear()
const m = now.getMonth() + 1
const d = now.getDate()

export default function DailyReportPage() {
  const [year, setYear] = useState(y)
  const [month, setMonth] = useState(m)
  const [day, setDay] = useState(d)
  const [data, setData] = useState<DailyReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchApi<DailyReport>(
        `/admin/daily?year=${year}&month=${month}&day=${day}`
      )
      setData(result)
    } catch {
      setError("Failed to load daily report")
    } finally {
      setLoading(false)
    }
  }, [year, month, day])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const daysInMonth = new Date(year, month, 0).getDate()

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

  const workers = [...new Set(data?.entries.map((e) => e.worker_name) || [])]
  const products = [...new Set(data?.entries.map((e) => e.product_code) || [])]

  const getQty = (worker: string, product: string) => {
    const entry = data?.entries.find(
      (e) => e.worker_name === worker && e.product_code === product
    )
    return entry?.quantity ?? "-"
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Daily Report</h1>

      <div className="mb-6 flex flex-wrap gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Year</label>
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Month</label>
          <input
            type="number"
            min={1}
            max={12}
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Day</label>
          <input
            type="number"
            min={1}
            max={daysInMonth}
            value={day}
            onChange={(e) => setDay(Number(e.target.value))}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
      </div>

      {!data || data.entries.length === 0 ? (
        <p className="text-gray-500">No data for this date.</p>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="whitespace-nowrap px-4 py-2 text-left font-medium text-gray-500">
                    Worker
                  </th>
                  {products.map((p) => (
                    <th
                      key={p}
                      className="whitespace-nowrap px-4 py-2 text-right font-medium text-gray-500"
                    >
                      {p}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {workers.map((worker) => (
                  <tr key={worker} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-2 font-medium text-gray-700">
                      {worker}
                    </td>
                    {products.map((p) => (
                      <td
                        key={p}
                        className="whitespace-nowrap px-4 py-2 text-right text-gray-700"
                      >
                        {getQty(worker, p)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}
