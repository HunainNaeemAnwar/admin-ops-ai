"use client"

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div
      className="flex min-h-dvh flex-col items-center justify-center gap-4 px-4"
      style={{ background: "var(--color-bg)" }}
    >
      <h1 className="text-xl font-semibold" style={{ color: "var(--color-destructive)" }}>
        Backend unavailable
      </h1>
      <p className="text-sm" style={{ color: "var(--color-muted)" }}>
        {error.message}
      </p>
      <button
        className="rounded-md bg-brand-green px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
        onClick={reset}
      >
        Try again
      </button>
    </div>
  )
}
