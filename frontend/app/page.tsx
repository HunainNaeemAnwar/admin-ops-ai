"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { Worker, Product } from "@/lib/types"
import { WorkerMonthTable } from "@/components/worker-month-table"
import { Select } from "@/components/ui/select"
import { ThemeToggle } from "@/components/theme-toggle"

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
      <div className="flex min-h-dvh items-center justify-center px-4" style={{ background: "var(--color-bg)" }}>
        <div className="flex flex-col items-center gap-4">
          <p className="text-lg font-medium" style={{ color: "var(--color-destructive)" }}>{error}</p>
          <button
            className="rounded-md px-4 py-2 text-sm font-medium text-white transition-opacity"
            style={{ background: "var(--color-success)" }}
            onClick={handleRetry}
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <main className="min-h-dvh px-4 py-6" style={{ background: "var(--color-bg)" }}>
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-xl font-bold sm:text-2xl" style={{ color: "var(--color-foreground)" }}>
            Factory Production
          </h1>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <a
              href="/login"
              className="rounded-md px-4 py-2 text-sm font-medium text-white transition-opacity"
              style={{ background: "var(--color-success)" }}
              onMouseEnter={(e) => e.currentTarget.style.opacity = "0.9"}
              onMouseLeave={(e) => e.currentTarget.style.opacity = "1"}
            >
              Admin Login
            </a>
          </div>
        </div>

        <div className="mb-6 flex flex-wrap gap-3">
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
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium" style={{ color: "var(--color-muted)" }}>Year</label>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="rounded-md border px-3 py-2 text-sm"
              style={{
                borderColor: "var(--color-border)",
                background: "var(--color-surface)",
                color: "var(--color-foreground)",
              }}
            >
              {[currentYear - 1, currentYear, currentYear + 1].map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
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
          <p className="py-8 text-center text-sm" style={{ color: "var(--color-muted)" }}>
            Loading workers...
          </p>
        )}
      </div>
    </main>
  )
}
