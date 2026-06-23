import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

export function proxy(request: NextRequest) {
  const authCookie = request.cookies.get("auth")
  const { pathname } = request.nextUrl

  if (pathname.startsWith("/admin")) {
    if (!authCookie) {
      const loginUrl = new URL("/login", request.url)
      return NextResponse.redirect(loginUrl)
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/admin/:path*"],
}
