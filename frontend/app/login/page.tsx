"use client"

import { useSearchParams } from "next/navigation"
import { Suspense } from "react"

function LoginContent() {
  const searchParams = useSearchParams()
  const expired = searchParams.get("expired")

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        {expired && (
          <div className="mb-4 rounded-md border border-yellow-300 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
            Session expired. Please sign in again.
          </div>
        )}
        <div className="rounded-lg border border-gray-200 bg-white p-8 shadow-sm">
          <h1 className="mb-2 text-xl font-semibold text-gray-900">
            Admin Login
          </h1>
          <p className="mb-6 text-sm text-gray-500">
            Sign in with your Google account to access the admin dashboard.
          </p>
          <a
            href={`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/admin/login`}
            className="inline-flex w-full items-center justify-center rounded-md bg-brand-blue px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            Sign in with Google
          </a>
        </div>
      </div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginContent />
    </Suspense>
  )
}
