"use client"

import { useEffect, useState, useCallback } from "react"
import Link from "next/link"
import { fetchApi } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { Avatar } from "@/components/ui/avatar"
import { Search, ChevronRight } from "lucide-react"

export default function WorkersListPage() {
  const [workers, setWorkers] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState("")

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

  const filtered = workers.filter((w) =>
    w.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-12 w-full" />
        {Array.from({ length: 8 }).map((_, i) => (
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
      <h1 className="text-xl font-bold sm:text-2xl" style={{ color: "var(--color-foreground)" }}>
        Workers
      </h1>

      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: "var(--color-muted)" }} />
        <input
          type="text"
          placeholder="Search workers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-md border py-2.5 pl-9 pr-3 text-sm"
          style={{
            borderColor: "var(--color-border)",
            background: "var(--color-surface)",
            color: "var(--color-foreground)",
          }}
        />
      </div>

      <div className="space-y-2">
        {filtered.map((name) => (
          <Link
            key={name}
            href={`/admin/worker/${encodeURIComponent(name)}`}
            className="flex items-center justify-between rounded-lg border px-4 py-3 text-sm font-medium transition-colors hover:border-brand-green"
            style={{
              borderColor: "var(--color-border)",
              background: "var(--color-surface)",
              color: "var(--color-foreground)",
            }}
          >
            <div className="flex items-center gap-3">
              <Avatar name={name} />
              <span>{name}</span>
            </div>
            <ChevronRight size={16} style={{ color: "var(--color-muted)" }} />
          </Link>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="py-8 text-center text-sm" style={{ color: "var(--color-muted)" }}>
          No workers found.
        </div>
      )}
    </div>
  )
}
