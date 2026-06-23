"use client"

import { useEffect, useState, useCallback } from "react"
import Link from "next/link"
import { fetchApi } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"

export default function WorkersListPage() {
  const [workers, setWorkers] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchApi<{ workers: string[] }>("/admin/workers")
      setWorkers(data.workers)
    } catch {
      setError("Failed to load workers")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-48" />
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-64" />
        ))}
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

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Workers</h1>
      <div className="space-y-2">
        {workers.map((name) => (
          <Link
            key={name}
            href={`/admin/worker/${encodeURIComponent(name)}`}
            className="block rounded-lg border border-gray-200 bg-white px-4 py-3 text-sm font-medium text-gray-700 hover:border-brand-blue hover:text-brand-blue transition-colors"
          >
            {name}
          </Link>
        ))}
      </div>
    </div>
  )
}
