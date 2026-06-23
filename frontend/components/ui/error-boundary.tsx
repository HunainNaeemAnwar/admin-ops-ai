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
          <p className="text-lg font-medium text-red-600">Something went wrong</p>
          <p className="text-sm text-gray-500">{this.state.error?.message}</p>
          <button
            className="rounded-md bg-brand-blue px-4 py-2 text-sm text-white hover:bg-blue-700"
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
      <p className="text-lg font-medium text-red-600">{message}</p>
      {onRetry && (
        <button
          className="rounded-md bg-brand-blue px-4 py-2 text-sm text-white hover:bg-blue-700"
          onClick={onRetry}
        >
          Retry
        </button>
      )}
    </div>
  )
}
