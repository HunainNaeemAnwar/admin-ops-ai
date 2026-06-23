"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { MonthlyReport } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
import { Select } from "@/components/ui/select"

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

  const productCodes =
    data && data.workers.length > 0
      ? [...new Set(data.workers.flatMap((w) => Object.keys(w.totals)))]
      : []

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Monthly Report</h1>

      <div className="mb-6 flex flex-wrap gap-4">
        <Select
          label="Month"
          options={MONTHS.map((m, i) => ({ value: String(i + 1), label: m }))}
          value={String(month)}
          onChange={(e) => setMonth(Number(e.target.value))}
        />
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700">Year</label>
          <input
            type="number"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </div>
      </div>

      {!data || data.workers.length === 0 ? (
        <p className="text-gray-500">No data for this period.</p>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="whitespace-nowrap px-4 py-2 text-left font-medium text-gray-500">
                    Worker
                  </th>
                  {productCodes.map((code) => (
                    <th
                      key={code}
                      className="whitespace-nowrap px-4 py-2 text-right font-medium text-gray-500"
                    >
                      {code}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {data.workers.map((w) => (
                  <tr key={w.worker} className="hover:bg-gray-50">
                    <td className="whitespace-nowrap px-4 py-2 font-medium text-gray-700">
                      {w.worker}
                    </td>
                    {productCodes.map((code) => (
                      <td
                        key={code}
                        className="whitespace-nowrap px-4 py-2 text-right text-gray-700"
                      >
                        {w.totals[code] ?? "-"}
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
