"use client"

import { use, useState } from "react"
import { WorkerMonthTable } from "@/components/worker-month-table"
import { Select } from "@/components/ui/select"
import { fetchApi } from "@/lib/api"
import type { Product } from "@/lib/types"
import { useEffect, useCallback } from "react"
import { Avatar } from "@/components/ui/avatar"
import { Download, ChevronLeft, ChevronRight, ArrowLeft } from "lucide-react"
import Link from "next/link"

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
]

const now = new Date()
const currentYear = now.getFullYear()
const currentMonth = now.getMonth() + 1

export default function WorkerDetailPage({
  params,
}: {
  params: Promise<{ name: string }>
}) {
  const { name } = use(params)
  const workerName = decodeURIComponent(name)
  const [year, setYear] = useState(currentYear)
  const [month, setMonth] = useState(currentMonth)
  const [products, setProducts] = useState<Product[]>([])

  const fetchProducts = useCallback(async () => {
    try {
      const data = await fetchApi<{ products: Product[] }>("/api/products")
      setProducts(data.products)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchProducts()
  }, [fetchProducts])

  const prevMonth = () => {
    if (month === 1) { setMonth(12); setYear(y => y - 1) }
    else setMonth(m => m - 1)
  }

  const nextMonth = () => {
    if (month === 12) { setMonth(1); setYear(y => y + 1) }
    else setMonth(m => m + 1)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <Link
          href="/admin/workers"
          className="rounded-md p-2 transition-colors hover:bg-surface-alt"
          style={{ color: "var(--color-muted)" }}
        >
          <ArrowLeft size={20} />
        </Link>
        <Avatar name={workerName} size="lg" />
        <h1 className="text-xl font-bold sm:text-2xl" style={{ color: "var(--color-foreground)" }}>
          {workerName}
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
           href={`/api/worker/${encodeURIComponent(workerName)}/excel/${year}/${month}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors"
          style={{ background: "var(--color-success)", color: "#FFFFFF" }}
        >
          <Download size={16} />
          Excel
        </a>
      </div>

      <WorkerMonthTable
        workerName={workerName}
        year={year}
        month={month}
        products={products}
      />
    </div>
  )
}
