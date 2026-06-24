"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, FileBarChart, Users, Receipt, MoreHorizontal } from "lucide-react"

const tabs = [
  { href: "/admin", icon: LayoutDashboard, label: "Home" },
  { href: "/admin/daily", icon: FileBarChart, label: "Daily" },
  { href: "/admin/monthly", icon: FileBarChart, label: "Monthly" },
  { href: "/admin/workers", icon: Users, label: "Workers" },
  { href: "/admin/payslips", icon: Receipt, label: "More" },
]

export function BottomNav() {
  const pathname = usePathname()

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 border-t bg-surface safe-bottom md:hidden"
      style={{ borderTopColor: "var(--color-border)" }}
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="flex items-center justify-around px-1 py-1">
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
              className={`flex flex-col items-center gap-0.5 rounded-md px-3 py-1.5 text-[10px] font-medium transition-colors ${
                isActive
                  ? "text-brand-green"
                  : "text-muted hover:text-foreground"
              }`}
            >
              <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
              <span>{tab.label}</span>
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
