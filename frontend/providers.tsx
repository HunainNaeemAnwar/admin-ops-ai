"use client"

import type { ReactNode } from "react"
import { AuthProvider } from "@/lib/auth"
import { ThemeProvider } from "@/lib/theme-context"
import { ToastProvider } from "@/lib/toast-context"

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ToastProvider>{children}</ToastProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}
