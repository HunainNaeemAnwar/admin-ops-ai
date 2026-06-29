"use client"

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from "react"
import { fetchApi, setAuthToken, clearAuthToken } from "./api"
import type { AuthUser } from "./types"

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  checkAuth: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue>({ user: null, loading: true, checkAuth: async () => {} })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  const checkAuth = useCallback(async () => {
    try {
      const data = await fetchApi<AuthUser>("/api/auth/me")
      if (data.authenticated) {
        setUser(data)
        if (data.token) {
          setAuthToken(data.token)
        }
      } else {
        setUser(null)
      }
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (typeof window !== "undefined" && window.location.pathname.startsWith("/auth/callback")) {
      setLoading(false)
      return
    }
    checkAuth()
  }, [checkAuth])

  return (
    <AuthContext.Provider value={{ user, loading, checkAuth }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
