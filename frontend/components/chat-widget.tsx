"use client"

import { useState, useEffect, useRef, type FormEvent } from "react"
import { ApiError } from "@/lib/api"
import type { ChatMessage } from "@/lib/types"

const STORAGE_KEY = "admin-chat-messages"
const TIMEOUT_MS = 120_000

function loadMessages(): ChatMessage[] {
  if (typeof window === "undefined") return []
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return parsed.map((m: ChatMessage) => ({
      ...m,
      timestamp: new Date(m.timestamp),
    }))
  } catch {
    return []
  }
}

function saveMessages(messages: ChatMessage[]) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
  } catch {
    // ignore
  }
}

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setMessages(loadMessages())
  }, [])

  useEffect(() => {
    saveMessages(messages)
  }, [messages])

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  const sendMessage = async (text: string) => {
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      text,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setLoading(true)

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS)

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || ""
      const res = await fetch(`${backendUrl}/admin/chat`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
        signal: controller.signal,
      })
      clearTimeout(timeoutId)

      if (!res.ok) throw new ApiError("Request failed", res.status)

      const data = await res.json()
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: data.response || "No response",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      let errorText: string
      if (err instanceof DOMException && err.name === "AbortError") {
        errorText = "Request timed out"
      } else if (err instanceof ApiError) {
        errorText = `Server error (${err.status}): ${err.message}`
      } else if (err instanceof TypeError) {
        errorText = "Cannot connect to backend. Is FastAPI running?"
      } else {
        errorText = "Error: Unable to reach server"
      }
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        text: errorText,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return
    sendMessage(input.trim())
  }

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {!isOpen ? (
        <button
          className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-blue text-2xl text-white shadow-lg hover:bg-blue-700 transition-colors"
          onClick={() => setIsOpen(true)}
        >
          💬
        </button>
      ) : (
        <div className="flex h-96 w-80 flex-col rounded-lg border border-gray-200 bg-white shadow-xl">
          <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
            <span className="text-sm font-semibold text-gray-900">
              Factory Assistant
            </span>
            <button
              className="text-gray-500 hover:text-gray-700"
              onClick={() => setIsOpen(false)}
            >
              ✕
            </button>
          </div>

          <div ref={listRef} className="flex-1 space-y-2 overflow-y-auto p-3">
            {messages.length === 0 && (
              <p className="py-8 text-center text-sm text-gray-400">
                Ask me anything about production
              </p>
            )}
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === "user"
                      ? "bg-brand-blue text-white"
                      : "bg-gray-100 text-gray-800"
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="max-w-[75%] rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-500">
                  <span className="animate-pulse">...</span>
                </div>
              </div>
            )}
          </div>

          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 border-t border-gray-200 px-3 py-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a message..."
              className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-brand-blue focus:outline-none"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="rounded-md bg-brand-blue px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
