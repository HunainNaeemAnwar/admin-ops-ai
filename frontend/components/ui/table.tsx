"use client"

import type { ReactNode } from "react"

interface Column<T> {
  key: string
  header: string
  sortable?: boolean
  render: (row: T) => ReactNode
}

interface TableProps<T> {
  columns: Column<T>[]
  data: T[]
  onSort?: (key: string) => void
  sortKey?: string
  sortDir?: "asc" | "desc"
}

function SortIcon({ active, dir }: { active: boolean; dir: "asc" | "desc" }) {
  return (
    <span className={`ml-1 inline-block text-xs ${active ? "text-brand-blue" : "text-gray-400"}`}>
      {active ? (dir === "asc" ? "▲" : "▼") : "⇅"}
    </span>
  )
}

export function Table<T>({
  columns,
  data,
  onSort,
  sortKey,
  sortDir = "asc",
}: TableProps<T>) {
  if (data.length === 0) {
    return <p className="py-4 text-center text-gray-500">No data</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 ${
                  col.sortable ? "cursor-pointer select-none hover:bg-gray-100" : ""
                }`}
                onClick={() => col.sortable && onSort?.(col.key)}
              >
                {col.header}
                {col.sortable && (
                  <SortIcon active={sortKey === col.key} dir={sortDir} />
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {data.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              {columns.map((col) => (
                <td key={col.key} className="whitespace-nowrap px-4 py-3 text-sm text-gray-700">
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
