export default function RootLoading() {
  return (
    <div className="flex min-h-dvh items-center justify-center" style={{ background: "var(--color-bg)" }}>
      <p className="animate-pulse text-sm" style={{ color: "var(--color-muted)" }}>
        Loading...
      </p>
    </div>
  )
}
