"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { PayslipListResponse } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
import { Select } from "@/components/ui/select"
import { FileText, Download } from "lucide-react"

const now = new Date()
const currentYear = now.getFullYear()
const currentMonth = now.getMonth() + 1

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
]

function parsePayslipName(name: string) {
  const parts = name.split("_")
  return { worker: parts[0] || name, year: parts[1] || "", month: parts[2] || "" }
}

export default function PayslipsPage() {
  const [year, setYear] = useState(currentYear)
  const [month, setMonth] = useState(currentMonth)
  const [data, setData] = useState<PayslipListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchApi<PayslipListResponse>(
        `/admin/payslips?year=${year}&month=${month}`
      )
      setData(result)
    } catch {
      setError("Failed to load payslips")
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

  const allNames = [...new Set([...(data?.pdfs || []), ...(data?.excels || [])])]
  const allWorkers = allNames.map((n) => ({ key: n, ...parsePayslipName(n) }))

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Payslips</h1>

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

      {!data || allWorkers.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12 text-gray-500">
          <FileText size={40} className="text-gray-300" />
          <p>No payslips generated for this period.</p>
          <p className="text-sm">Ask the AI chatbot to generate payslips.</p>
        </div>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="whitespace-nowrap px-4 py-2 text-left font-medium text-gray-500">
                    Worker
                  </th>
                  <th className="whitespace-nowrap px-4 py-2 text-center font-medium text-gray-500">
                    PDF
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {allWorkers.map((p) => {
                  const hasPdf = data.pdfs.includes(p.key)
                  return (
                    <tr key={p.key} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-4 py-2 font-medium text-gray-700">
                        {p.worker}
                      </td>
                      <td className="whitespace-nowrap px-4 py-2 text-center">
                        {hasPdf ? (
                          <a
                            href={`${backendUrl}/admin/payslip/pdf/${p.worker}/${p.year}/${p.month}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 rounded-md bg-green-50 px-3 py-1 text-xs font-medium text-green-700 hover:bg-green-100"
                          >
                            <Download size={14} />
                            PDF
                          </a>
                        ) : (
                          <span className="text-gray-300">-</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}