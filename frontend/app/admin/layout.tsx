"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth"
import { AdminSidebar } from "@/components/admin-sidebar"
import { ChatWidgetLoader } from "@/components/chat-widget-loader"
import { BottomNav } from "@/components/bottom-nav"

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { user, loading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!loading && !user?.authenticated) {
      router.replace("/login?expired=true")
    }
    if (!loading && user?.authenticated && !user?.is_father) {
      router.replace("/")
    }
  }, [loading, user, router])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center" style={{ background: "var(--color-bg)" }}>
        <p style={{ color: "var(--color-muted)" }}>Loading...</p>
      </div>
    )
  }

  if (!user?.is_father) {
    return null
  }

  return (
    <div className="flex min-h-dvh">
      <AdminSidebar />
      <main
        className="flex-1 overflow-auto pb-20 md:pb-6"
        style={{ background: "var(--color-bg)" }}
      >
        <div className="p-4 sm:p-6">
          {children}
        </div>
      </main>
      <BottomNav />
      <ChatWidgetLoader />
    </div>
  )
}
