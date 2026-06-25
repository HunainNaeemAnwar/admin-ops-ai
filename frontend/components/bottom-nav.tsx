"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { LayoutDashboard, FileBarChart, Users, Receipt, Settings, X, Sun, Moon, LogOut } from "lucide-react"
import { useTheme } from "@/lib/theme-context"
import { fetchApi } from "@/lib/api"

const tabs = [
  { href: "/admin", icon: LayoutDashboard, label: "Home" },
  { href: "/admin/daily", icon: FileBarChart, label: "Daily" },
  { href: "/admin/monthly", icon: FileBarChart, label: "Monthly" },
  { href: "/admin/workers", icon: Users, label: "Workers" },
  { href: "/admin/payslips", icon: Receipt, label: "Payslips" },
]

export function BottomNav() {
  const pathname = usePathname()
  const router = useRouter()
  const { theme, toggle } = useTheme()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden"
    } else {
      document.body.style.overflow = ""
    }
    return () => { document.body.style.overflow = "" }
  }, [open])

  const handleLogout = async () => {
    try {
      await fetchApi("/api/auth/logout", { method: "POST" })
    } catch { /* ignore */ }
    router.push("/login")
  }

  return (
    <>
      <nav
        className="fixed bottom-0 left-0 right-0 z-50 border-t safe-bottom md:hidden"
        style={{
          borderTopColor: "var(--color-border)",
          background: "var(--color-surface)",
        }}
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="flex items-center justify-around px-2 py-1.5">
          {tabs.map((tab) => {
            const isActive =
              tab.href === "/admin"
                ? pathname === "/admin" || pathname === "/admin/"
                : pathname.startsWith(tab.href)
            const Icon = tab.icon

            return (
              <Link
                key={tab.href}
                href={tab.href}
                className="flex flex-col items-center gap-0.5 rounded-xl px-3 py-1.5 text-[10px] font-semibold transition-all duration-150"
                style={{ color: isActive ? "var(--color-primary)" : "var(--color-muted)" }}
              >
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-lg transition-all duration-150"
                  style={isActive ? { background: "var(--color-surface-alt)" } : undefined}
                >
                  <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
                </div>
                <span>{tab.label}</span>
              </Link>
            )
          })}

          <button
            onClick={() => setOpen(true)}
            className="flex flex-col items-center gap-0.5 rounded-xl px-3 py-1.5 text-[10px] font-semibold transition-all duration-150"
            style={{ color: "var(--color-muted)" }}
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg">
              <Settings size={20} />
            </div>
            <span>More</span>
          </button>
        </div>
      </nav>

      {open && (
        <div className="fixed inset-0 z-[60] md:hidden" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-black/40" />
          <div
            className="absolute bottom-0 left-0 right-0 rounded-t-2xl px-4 pb-8 pt-3 safe-bottom"
            style={{ background: "var(--color-surface)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between px-1">
              <span className="text-sm font-bold" style={{ color: "var(--color-foreground)" }}>Settings</span>
              <button
                onClick={() => setOpen(false)}
                className="rounded-lg p-1.5 transition-colors"
                style={{ color: "var(--color-muted)" }}
                onMouseEnter={(e) => e.currentTarget.style.background = "var(--color-surface-alt)"}
                onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-1">
              <button
                onClick={toggle}
                className="flex w-full items-center gap-4 rounded-xl px-4 py-3.5 text-sm font-semibold transition-colors"
                style={{ color: "var(--color-foreground)" }}
                onMouseEnter={(e) => e.currentTarget.style.background = "var(--color-surface-alt)"}
                onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
              >
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ background: "var(--color-surface-alt)", color: "var(--color-primary)" }}
                >
                  {theme === "dark" ? <Sun size={20} /> : <Moon size={20} />}
                </div>
                <span>{theme === "dark" ? "Light Mode" : "Dark Mode"}</span>
              </button>

              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-4 rounded-xl px-4 py-3.5 text-sm font-semibold transition-colors"
                style={{ color: "var(--color-destructive)" }}
                onMouseEnter={(e) => e.currentTarget.style.background = "var(--color-surface-alt)"}
                onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
              >
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-xl"
                  style={{ background: "var(--color-surface-alt)", color: "var(--color-destructive)" }}
                >
                  <LogOut size={20} />
                </div>
                <span>Logout</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
