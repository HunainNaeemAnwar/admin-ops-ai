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
import { fetchApi, clearAuthToken } from "@/lib/api"
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
    try { await fetchApi("/api/auth/logout", { method: "POST" }) } catch { /* ignore */ }
    clearAuthToken()
    router.push("/login")
  }

  return (
    <aside
      className={`hidden flex-col border-r transition-all duration-200 md:flex ${collapsed ? "w-16" : "w-56"}`}
      style={{
        borderColor: "var(--color-border)",
        background: "var(--color-sidebar)",
      }}
    >
      {/* Logo */}
      <div className="flex items-center justify-between border-b px-4 py-4" style={{ borderColor: "var(--color-border)" }}>
        {!collapsed && (
          <div className="flex items-center gap-2.5">
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
          className="rounded-lg p-1.5 transition-colors hover:opacity-70"
          style={{ color: "var(--color-sidebar-text)" }}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-0.5 px-2 py-4">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = pathname === item.href || (item.href === "/admin" && pathname === "/admin/")
          return (
            <Link
              key={item.href}
              href={item.href}
              className="group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150"
              style={{
                background: isActive ? "var(--color-sidebar-active-bg)" : "transparent",
                color: isActive ? "var(--color-sidebar-text-active)" : "var(--color-sidebar-text)",
              }}
              onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = "var(--color-sidebar-hover)" }}
              onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = "transparent" }}
            >
              {isActive && (
                <span
                  className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-full"
                  style={{ background: "var(--color-sidebar-active-border)" }}
                />
              )}
              <Icon size={18} strokeWidth={isActive ? 2.5 : 2} />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Bottom */}
      <div className="space-y-0.5 border-t px-2 py-3" style={{ borderColor: "var(--color-border)" }}>
        <ThemeToggle />
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors"
          style={{ color: "var(--color-sidebar-text)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.color = "var(--color-destructive)"
            e.currentTarget.style.background = "var(--color-sidebar-hover)"
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.color = "var(--color-sidebar-text)"
            e.currentTarget.style.background = "transparent"
          }}
        >
          <LogOut size={18} />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  )
}
