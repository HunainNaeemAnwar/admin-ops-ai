"use client"

import { useEffect, useState, useCallback } from "react"
import { fetchApi } from "@/lib/api"
import type { Product } from "@/lib/types"
import { Skeleton } from "@/components/ui/skeleton"
import { Card } from "@/components/ui/card"
import { Breadcrumbs } from "@/components/ui/breadcrumbs"
import { Package } from "lucide-react"

export default function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchApi<{ products: Product[] }>("/admin/products")
      setProducts(data.products)
    } catch {
      setError("Failed to load products")
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
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-14 w-full" />
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-4 py-12">
        <p style={{ color: "var(--color-destructive)" }}>{error}</p>
        <button
          className="rounded-md bg-brand-green px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
          onClick={fetchData}
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Breadcrumbs />

      <h1 className="text-xl font-bold sm:text-2xl" style={{ color: "var(--color-foreground)" }}>
        Products
      </h1>

      <Card>
        <div className="swipeable-scroll overflow-x-auto">
          <table className="min-w-full text-sm" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "2px solid var(--color-border)" }}>
                <th
                  className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "var(--color-muted)" }}
                >
                  Code
                </th>
                <th
                  className="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider"
                  style={{ color: "var(--color-muted)" }}
                >
                  Rate (Rs)
                </th>
              </tr>
            </thead>
            <tbody>
              {products.map((p, i) => (
                <tr
                  key={p.id}
                  style={{
                    borderBottom: "1px solid var(--color-border)",
                    background: i % 2 === 0 ? "var(--color-surface)" : "var(--color-table-stripe)",
                  }}
                  className="transition-colors hover:bg-surface-alt"
                >
                  <td className="px-4 py-3 font-medium">
                    <div className="flex items-center gap-2">
                      <div
                        className="flex h-8 w-8 items-center justify-center rounded-md"
                        style={{ background: "var(--color-surface-alt)" }}
                      >
                        <Package size={14} style={{ color: "var(--color-muted)" }} />
                      </div>
                      <span style={{ color: "var(--color-foreground)" }}>{p.code}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-mono font-semibold" style={{ color: "var(--color-foreground)" }}>
                    Rs {p.rate.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
