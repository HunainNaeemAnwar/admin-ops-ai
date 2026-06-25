"use client"

import { useSearchParams } from "next/navigation"
import { Suspense } from "react"
import { ThemeToggle } from "@/components/theme-toggle"

function LoginContent() {
  const searchParams = useSearchParams()
  const expired = searchParams.get("expired")

  return (
    <div className="flex min-h-dvh items-center justify-center px-4" style={{ background: "var(--color-bg)" }}>
      <div className="w-full max-w-sm">
        {expired && (
          <div
            className="mb-4 rounded-md border px-4 py-3 text-sm"
            style={{
              borderColor: "var(--color-warning)",
              background: "rgba(245, 158, 11, 0.1)",
              color: "var(--color-warning)",
            }}
          >
            Session expired. Please sign in again.
          </div>
        )}
        <div
          className="rounded-lg border p-8 shadow-sm"
          style={{
            borderColor: "var(--color-border)",
            background: "var(--color-surface)",
          }}
        >
          <h1
            className="mb-2 text-xl font-semibold"
            style={{ color: "var(--color-foreground)" }}
          >
            Admin Login
          </h1>
          <p className="mb-6 text-sm" style={{ color: "var(--color-muted)" }}>
            Sign in with your Google account to access the admin dashboard.
          </p>
          <a
            href={`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/admin/login`}
            className="inline-flex w-full items-center justify-center rounded-md px-4 py-2.5 text-sm font-medium text-white transition-opacity min-h-[44px]"
            style={{ background: "var(--color-success)" }}
            onMouseEnter={(e) => e.currentTarget.style.opacity = "0.9"}
            onMouseLeave={(e) => e.currentTarget.style.opacity = "1"}
          >
            Sign in with Google
          </a>
          <div className="mt-4 flex justify-center">
            <ThemeToggle />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginContent />
    </Suspense>
  )
}
