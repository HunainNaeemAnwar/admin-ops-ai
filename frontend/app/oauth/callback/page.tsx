"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { fetchApi } from "@/lib/api"
import type { AuthUser } from "@/lib/types"

export default function OAuthCallbackPage() {
  const router = useRouter()
  const [status, setStatus] = useState("Processing login...")

  useEffect(() => {
    fetchApi<AuthUser>("/api/auth/me")
      .then((user) => {
        if (user.authenticated) {
          router.replace(user.is_father ? "/admin" : "/")
        } else {
          setStatus("Login failed. Please try again.")
        }
      })
      .catch(() => {
        setStatus("Backend unavailable. Please ensure FastAPI is running.")
      })
  }, [router])

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-gray-500">{status}</p>
    </div>
  )
}
