"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import {
  LayoutDashboard,
  Calendar,
  BarChart3,
  Users,
  Package,
  FileText,
  LogOut,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import { useState } from "react"
import { fetchApi } from "@/lib/api"
import { ThemeToggle } from "@/components/theme-toggle"

const navItems = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard },
  { href: "/admin/daily", label: "Daily", icon: Calendar },
  { href: "/admin/monthly", label: "Monthly", icon: BarChart3 },
  { href: "/admin/workers", label: "Workers", icon: Users },
  { href: "/admin/products", label: "Products", icon: Package },
  { href: "/admin/payslips", label: "Payslips", icon: FileText },
]

export function AdminSidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const [collapsed, setCollapsed] = useState(false)

  const handleLogout = async () => {
    try {
      await fetchApi("/api/auth/logout", { method: "POST" })
    } catch {
      // ignore
    }
    router.push("/login")
  }

  return (
    <aside
      className={`hidden flex-col border-r transition-all duration-200 md:flex ${
        collapsed ? "w-16" : "w-56"
      }`}
      style={{
        borderColor: "var(--color-border)",
        background: "var(--color-surface)",
      }}
    >
      <div className="flex items-center justify-between border-b px-4 py-4" style={{ borderColor: "var(--color-border)" }}>
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-lg text-xs font-bold"
              style={{ background: "var(--color-primary)", color: "var(--color-on-primary)" }}
            >
              AO
            </div>
            <span className="text-sm font-bold" style={{ color: "var(--color-foreground)" }}>
              Admin Ops
            </span>
          </div>
        )}
        <button
          className="rounded-lg p-1.5 transition-colors"
          style={{ color: "var(--color-muted)" }}
          onClick={() => setCollapsed(!collapsed)}
          onMouseEnter={(e) => e.currentTarget.style.background = "var(--color-surface-alt)"}
          onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <nav className="flex-1 space-y-1 px-2 py-4">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href || (item.href === "/admin" && pathname === "/admin/")
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150"
              style={{
                background: isActive ? "var(--color-primary)" : "transparent",
                color: isActive ? "var(--color-on-primary)" : "var(--color-muted)",
              }}
              onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = "var(--color-surface-alt)" }}
              onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = "transparent" }}
            >
              <Icon size={18} />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          )
        })}
      </nav>

      <div className="space-y-1 border-t px-2 py-3" style={{ borderColor: "var(--color-border)" }}>
        <ThemeToggle />
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors"
          style={{ color: "var(--color-muted)" }}
          onMouseEnter={(e) => { e.currentTarget.style.color = "var(--color-destructive)"; e.currentTarget.style.background = "var(--color-surface-alt)" }}
          onMouseLeave={(e) => { e.currentTarget.style.color = "var(--color-muted)"; e.currentTarget.style.background = "transparent" }}
        >
          <LogOut size={18} />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  )
}
