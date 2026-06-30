"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { DailyReport } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Toast } from "@/components/ui/toast"
import { ConfirmModal } from "@/components/ui/confirm-modal"
import { Calendar, Trash2 } from "lucide-react"

export default function DailyReportPage() {
  const [dateStr, setDateStr] = useState(() => {
    const now = new Date()
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`
  })
  const [data, setData] = useState<DailyReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [y, m, d] = dateStr.split("-").map(Number)
      const result = await fetchApi<DailyReport>(
        `/admin/daily?year=${y}&month=${m}&day=${d}`
      )
      setData(result)
    } catch {
      setError("Failed to load daily report")
    } finally {
      setLoading(false)
    }
  }, [dateStr])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const goToToday = () => {
    const now = new Date()
    setDateStr(
      `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`
    )
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await fetchApi(`/admin/date/${dateStr}`, { method: "DELETE" })
      setToast({ message: `Data for ${dateStr} deleted.`, type: "success" })
      setShowDeleteModal(false)
      fetchData()
    } catch {
      setToast({ message: "Failed to delete data.", type: "error" })
    } finally {
      setDeleting(false)
    }
  }

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
        <p style={{ color: "var(--color-destructive)" }}>{error}</p>
        <button
          className="rounded-lg bg-brand-blue px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors shadow-sm"
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
    return entry?.quantity ?? null
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold sm:text-2xl" style={{ color: "var(--color-foreground)" }}>
          Daily Report
        </h1>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1 flex flex-col gap-1.5">
          <label className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--color-muted)" }}>
            Date
          </label>
          <input
            type="date"
            value={dateStr}
            onChange={(e) => setDateStr(e.target.value)}
            className="input-base"
          />
        </div>
        <button
          onClick={goToToday}
          className="inline-flex items-center justify-center gap-2 rounded-lg border-2 px-4 py-2.5 text-sm font-semibold transition-colors"
          style={{ borderColor: "var(--color-border)", color: "var(--color-muted)" }}
        >
          <Calendar size={16} />
          Today
        </button>
        {data && data.entries.length > 0 && (
          <Button
            variant="danger"
            onClick={() => setShowDeleteModal(true)}
          >
            <Trash2 size={16} />
            Delete Day
          </Button>
        )}
      </div>

      {!data || data.entries.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed py-12 text-center" style={{ borderColor: "var(--color-border)" }}>
          <Calendar size={40} className="mx-auto mb-3" style={{ color: "var(--color-muted-light)" }} />
          <p className="text-sm font-medium" style={{ color: "var(--color-muted)" }}>
            No data for this date.
          </p>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2">
            <Badge variant="info">Workers: {workers.length}</Badge>
          </div>

          <Card>
            <div className="swipeable-scroll overflow-x-auto">
              <table className="min-w-full text-sm" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid var(--color-border)" }}>
                    <th
                      className="sticky left-0 z-10 px-4 py-3 text-left text-xs font-bold uppercase tracking-wider"
                      style={{ color: "var(--color-muted)", background: "var(--color-surface)" }}
                    >
                      Worker
                    </th>
                    {products.map((p) => (
                      <th
                        key={p}
                        className="whitespace-nowrap px-4 py-3 text-right text-xs font-bold uppercase tracking-wider"
                        style={{ color: "var(--color-muted)" }}
                      >
                        {p}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {workers.map((worker, i) => (
                    <tr
                      key={worker}
                      style={{
                        borderBottom: "1px solid var(--color-border)",
                        background: i % 2 === 0 ? "var(--color-surface)" : "var(--color-table-stripe)",
                      }}
                      className="transition-colors"
                    >
                      <td
                        className="sticky left-0 z-10 flex items-center gap-3 whitespace-nowrap px-4 py-3 font-semibold"
                        style={{ background: i % 2 === 0 ? "var(--color-surface)" : "var(--color-table-stripe)" }}
                      >
                        <Avatar name={worker} size="sm" />
                        <span style={{ color: "var(--color-foreground)" }}>{worker}</span>
                      </td>
                      {products.map((p) => {
                        const qty = getQty(worker, p)
                        return (
                          <td
                            key={p}
                            className="whitespace-nowrap px-4 py-3 text-right font-mono font-semibold tabular-nums"
                            style={{ color: "var(--color-foreground)" }}
                          >
                            {qty !== null ? qty.toLocaleString() : (
                              <span style={{ color: "var(--color-muted-light)" }}>-</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}

      <ConfirmModal
        open={showDeleteModal}
        title="Delete Day's Data"
        message={`This will permanently delete ALL production entries for ${dateStr}. Workers can be marked absent or production re-entered after deletion. This action cannot be undone.`}
        confirmLabel="Delete Forever"
        countdown={3}
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setShowDeleteModal(false)}
        loading={deleting}
      />
    </div>
  )
}
