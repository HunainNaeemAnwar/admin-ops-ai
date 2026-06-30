import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function middleware(request: NextRequest) {
  const token = request.cookies.get("auth")?.value
  const { pathname } = request.nextUrl

  const isAdminPage = pathname === "/admin" || (pathname.startsWith("/admin/") && pathname !== "/admin/login" && pathname !== "/admin/logout")

  if (isAdminPage && !token) {
    const loginUrl = new URL("/login", request.url)
    loginUrl.searchParams.set("expired", "true")
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/admin/:path*", "/admin"],
}
