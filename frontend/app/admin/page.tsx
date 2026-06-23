"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { DailyReport } from "@/lib/types"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

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
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
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

  const workerCount = data
    ? new Set(data.entries.map((e) => e.worker_name)).size
    : 0

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        Admin Overview
      </h1>

      {!data || data.entries.length === 0 ? (
        <p className="text-gray-500">No data yet today.</p>
      ) : (
        <>
          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Card title="Workers Today">
              <p className="text-3xl font-bold text-brand-blue">{workerCount}</p>
            </Card>
            <Card title="Total Pieces">
              <p className="text-3xl font-bold text-brand-blue">
                {data.total_pieces}
              </p>
            </Card>
            <Card title="Date">
              <p className="text-lg font-medium text-gray-700">{data.date}</p>
            </Card>
          </div>

          <Card title="Product Breakdown">
            <div className="space-y-2">
              {Object.entries(data.totals).map(([product, qty]) => (
                <div
                  key={product}
                  className="flex items-center justify-between border-b border-gray-100 py-1 last:border-0"
                >
                  <span className="font-medium text-gray-700">{product}</span>
                  <span className="text-gray-900">{qty}</span>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
