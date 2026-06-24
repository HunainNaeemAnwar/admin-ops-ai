"use client"

import { Component, type ReactNode, type ErrorInfo } from "react"

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, info)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }
      return (
        <div className="flex flex-col items-center justify-center gap-4 p-8">
          <p className="text-lg font-medium" style={{ color: "var(--color-destructive)" }}>
            Something went wrong
          </p>
          <p className="text-sm" style={{ color: "var(--color-muted)" }}>
            {this.state.error?.message}
          </p>
          <button
            className="rounded-md bg-brand-green px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}

export function FallbackError({
  message = "Backend unavailable",
  onRetry,
}: {
  message?: string
  onRetry?: () => void
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 p-12">
      <p className="text-lg font-medium" style={{ color: "var(--color-destructive)" }}>
        {message}
      </p>
      {onRetry && (
        <button
          className="rounded-md bg-brand-green px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition-opacity"
          onClick={onRetry}
        >
          Retry
        </button>
      )}
    </div>
  )
}
