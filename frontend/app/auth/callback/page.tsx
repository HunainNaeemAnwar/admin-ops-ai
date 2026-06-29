"use client"

import { useEffect, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { setAuthToken } from "@/lib/api"
import { useAuth } from "@/lib/auth"

function CallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { checkAuth } = useAuth()

  useEffect(() => {
    const token = searchParams.get("token")
    const isAdmin = searchParams.get("is_admin") === "true"

    if (!token) {
      router.replace("/login")
      return
    }

    setAuthToken(token)
    document.cookie = `auth=${token}; path=/; max-age=259200; samesite=lax`

    if (!isAdmin) {
      router.replace("/login?error=unauthorized")
      return
    }

    checkAuth().then(() => {
      router.replace("/admin")
    })
  }, [searchParams, router, checkAuth])

  return (
    <div className="flex min-h-dvh items-center justify-center" style={{ background: "var(--color-bg)" }}>
      <p style={{ color: "var(--color-muted)" }}>Signing in...</p>
    </div>
  )
}

export default function AuthCallbackPage() {
  return (
    <Suspense>
      <CallbackContent />
    </Suspense>
  )
}
