const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || ""

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

export async function fetchApi<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BACKEND_URL}${path}`

  const method = options?.method || "GET"
  const headers: Record<string, string> = { ...(options?.headers as Record<string, string>) }
  if (method !== "GET") {
    headers["Content-Type"] = "application/json"
  }

  const res = await fetch(url, {
    ...options,
    credentials: "include",
    headers,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new ApiError(
      text || `Request failed with status ${res.status}`,
      res.status
    )
  }

  return res.json() as Promise<T>
}
