"use client"

import { useEffect, useState } from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "@/lib/theme-context"

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggle } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  if (!mounted) {
    return (
      <button
        className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${className}`}
        style={{ color: "var(--color-muted)" }}
        aria-label="Toggle theme"
      >
        <div className="h-4 w-4" />
      </button>
    )
  }

  return (
    <button
      onClick={toggle}
      className={`inline-flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${className}`}
      style={{ color: "var(--color-muted)" }}
      onMouseEnter={(e) => e.currentTarget.style.background = "var(--color-surface-alt)"}
      onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
      aria-label={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
    >
      {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
      <span className="hidden sm:inline">{theme === "light" ? "Dark" : "Light"}</span>
    </button>
  )
}
