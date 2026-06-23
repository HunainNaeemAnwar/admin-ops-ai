"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth"
import { AdminSidebar } from "@/components/admin-sidebar"
import { ChatWidgetLoader } from "@/components/chat-widget-loader"

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
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading...</p>
      </div>
    )
  }

  if (!user?.is_father) {
    return null
  }

  return (
    <div className="flex min-h-screen">
      <AdminSidebar />
      <main className="flex-1 overflow-auto bg-gray-50 p-6">
        {children}
      </main>
      <ChatWidgetLoader />
    </div>
  )
}
