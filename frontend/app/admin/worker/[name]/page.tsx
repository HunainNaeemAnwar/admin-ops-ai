"use client"

import { use, useState } from "react"
import { WorkerMonthTable } from "@/components/worker-month-table"
import { Select } from "@/components/ui/select"
import { fetchApi } from "@/lib/api"
import type { Product } from "@/lib/types"
import { useEffect, useCallback } from "react"

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
  const [year, setYear] = useState(currentYear)
  const [month, setMonth] = useState(currentMonth)
  const [products, setProducts] = useState<Product[]>([])

  const fetchData = useCallback(async () => {
    try {
      const data = await fetchApi<{ products: Product[] }>("/api/products")
      setProducts(data.products)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">
        {decodeURIComponent(name)}
      </h1>

      <div className="mb-6 flex flex-wrap items-end gap-4">
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
        <a
          href={`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/api/worker/${encodeURIComponent(decodeURIComponent(name))}/excel/${year}/${month}`}
          className="inline-flex items-center rounded-md bg-green-600 px-4 py-2 text-sm text-white hover:bg-green-700 transition-colors"
        >
          Download Excel
        </a>
      </div>

      <WorkerMonthTable
        workerName={decodeURIComponent(name)}
        year={year}
        month={month}
        products={products}
      />
    </div>
  )
}
