export const BACKEND_URL: string =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000"

function apiUrl(path: string): string {
  if (path.startsWith("http")) return path
  return `${BACKEND_URL}${path}`
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

let _token: string | null = null

export function setAuthToken(token: string) {
  _token = token
  if (typeof window !== "undefined") {
    localStorage.setItem("auth_token", token)
  }
}

export function clearAuthToken() {
  _token = null
  if (typeof window !== "undefined") {
    localStorage.removeItem("auth_token")
  }
}

function getToken(): string | null {
  if (_token) return _token
  if (typeof window !== "undefined") {
    _token = localStorage.getItem("auth_token")
    return _token
  }
  return null
}

async function tryRefresh(): Promise<string | null> {
  const old = getToken()
  if (!old) return null
  try {
    const res = await fetch(apiUrl("/api/auth/refresh"), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", "X-Auth-Token": old },
    })
    if (!res.ok) return null
    const data = await res.json()
    if (data.token) {
      setAuthToken(data.token)
      return data.token
    }
    return null
  } catch {
    return null
  }
}

export async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = apiUrl(path)
  const method = options?.method || "GET"
  const headers: Record<string, string> = { ...(options?.headers as Record<string, string>) }
  if (method !== "GET") {
    headers["Content-Type"] = "application/json"
  }

  const token = getToken()
  if (token) {
    headers["X-Auth-Token"] = token
  }

  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers,
  })

  if (res.status === 401 && token) {
    const newToken = await tryRefresh()
    if (newToken) {
      headers["X-Auth-Token"] = newToken
      const retry = await fetch(url, {
        ...options,
        credentials: "include",
        headers,
      })
      if (retry.ok) {
        return retry.json() as Promise<T>
      }
    }
    clearAuthToken()
    if (typeof window !== "undefined") {
      window.location.href = "/login?expired=true"
    }
    throw new ApiError("Session expired", 401)
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new ApiError(
      text || `Request failed with status ${res.status}`,
      res.status
    )
  }

  return res.json() as Promise<T>
}
