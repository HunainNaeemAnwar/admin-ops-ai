"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { Worker, Product } from "@/lib/types"
import { WorkerMonthTable } from "@/components/worker-month-table"
import { Select } from "@/components/ui/select"

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
]

const now = new Date()
const currentYear = now.getFullYear()
const currentMonth = now.getMonth() + 1

export default function HomePage() {
  const [workers, setWorkers] = useState<Worker[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [selectedWorker, setSelectedWorker] = useState("")
  const [year, setYear] = useState(currentYear)
  const [month, setMonth] = useState(currentMonth)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchApi<{ workers: Worker[] }>("/api/workers")
      .then((data) => {
        setWorkers(data.workers)
        if (data.workers.length > 0) setSelectedWorker(data.workers[0].name)
      })
      .catch(() => setError("Backend unavailable"))

    fetchApi<{ products: Product[] }>("/api/products")
      .then((data) => setProducts(data.products))
      .catch(() => setError("Backend unavailable"))
  }, [])

  const isCurrentMonth = year === currentYear && month === currentMonth
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    if (!isCurrentMonth) return

    const id = setInterval(() => {
      if (!document.hidden) {
        setRefreshKey((k) => k + 1)
      }
    }, 15000)
    return () => clearInterval(id)
  }, [isCurrentMonth])

  const handleRetry = useCallback(() => {
    setError(null)
    window.location.reload()
  }, [])

  if (error && workers.length === 0) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <p className="text-lg font-medium text-red-600">{error}</p>
          <button
            className="rounded-md bg-brand-blue px-4 py-2 text-sm text-white hover:bg-blue-700"
            onClick={handleRetry}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <main className="mx-auto max-w-6xl px-4 py-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">
          Factory Production Dashboard
        </h1>
        <a
          href="/login"
          className="rounded-md bg-brand-blue px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          Admin Login
        </a>
      </div>

      <div className="mb-6 flex flex-wrap gap-4">
        <Select
          label="Worker"
          options={workers.map((w) => ({ value: w.name, label: w.name }))}
          value={selectedWorker}
          onChange={(e) => setSelectedWorker(e.target.value)}
        />
        <Select
          label="Month"
          options={MONTHS.map((m, i) => ({ value: String(i + 1), label: m }))}
          value={String(month)}
          onChange={(e) => setMonth(Number(e.target.value))}
        />
        <Select
          label="Year"
          options={[currentYear - 1, currentYear, currentYear + 1].map((y) => ({
            value: String(y),
            label: String(y),
          }))}
          value={String(year)}
          onChange={(e) => setYear(Number(e.target.value))}
        />
      </div>

      {selectedWorker ? (
        <WorkerMonthTable
          workerName={selectedWorker}
          year={year}
          month={month}
          products={products}
          refreshKey={refreshKey}
        />
      ) : (
        <p className="py-8 text-center text-gray-500">Loading workers...</p>
      )}
    </main>
  )
}
