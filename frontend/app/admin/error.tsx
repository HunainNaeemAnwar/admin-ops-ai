"use client"

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-xl font-semibold text-red-600">Backend unavailable</h1>
      <p className="text-sm text-gray-500">{error.message}</p>
      <button
        className="rounded-md bg-brand-blue px-4 py-2 text-sm text-white hover:bg-blue-700"
        onClick={reset}
      >
        Try again
      </button>
    </div>
  )
}
