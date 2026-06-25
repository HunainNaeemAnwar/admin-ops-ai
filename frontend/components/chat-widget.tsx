"use client"

import { useState, useEffect, useRef, type FormEvent } from "react"
import { ApiError } from "@/lib/api"
import type { ChatMessage } from "@/lib/types"
import { MessageCircle, X, Send, Loader2 } from "lucide-react"

const STORAGE_KEY = "admin-chat-messages"
const TIMEOUT_MS = 120_000

function loadMessages(): ChatMessage[] {
  if (typeof window === "undefined") return []
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    return JSON.parse(raw).map((m: ChatMessage) => ({ ...m, timestamp: new Date(m.timestamp) }))
  } catch { return [] }
}

function saveMessages(msgs: ChatMessage[]) {
  try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(msgs)) } catch {}
}

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { setMessages(loadMessages()) }, [])
  useEffect(() => { saveMessages(messages) }, [messages])
  useEffect(() => { if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight }, [messages])
  useEffect(() => { if (isOpen) setTimeout(() => inputRef.current?.focus(), 100) }, [isOpen])

  const send = async (text: string) => {
    setMessages((p) => [...p, { id: crypto.randomUUID(), role: "user", text, timestamp: new Date() }])
    setInput(""); setLoading(true)
    try {
      const c = new AbortController()
      const t = setTimeout(() => c.abort(), TIMEOUT_MS)
      const r = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/admin/chat`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }), signal: c.signal,
      })
      clearTimeout(t)
      if (!r.ok) throw new ApiError("fail", r.status)
      const d = await r.json()
      setMessages((p) => [...p, { id: crypto.randomUUID(), role: "assistant", text: d.response || "No response", timestamp: new Date() }])
    } catch (e) {
      let t = "Cannot reach server"
      if (e instanceof ApiError) t = `Error ${e.status}`
      else if (e instanceof TypeError) t = "Backend offline"
      setMessages((p) => [...p, { id: crypto.randomUUID(), role: "assistant", text: t, timestamp: new Date() }])
    } finally { setLoading(false) }
  }

  const onSubmit = (e: FormEvent) => { e.preventDefault(); if (input.trim() && !loading) send(input.trim()) }

  const bg = "var(--color-surface)"
  const border = "var(--color-border)"
  const fg = "var(--color-foreground)"
  const muted = "var(--color-muted)"
  const alt = "var(--color-surface-alt)"
  const primary = "var(--color-primary)"
  const onPrimary = "var(--color-on-primary)"

  return (
    <>
      {/* FAB */}
      {!isOpen && (
        <button onClick={() => setIsOpen(true)} aria-label="Open chat"
          className="fixed z-50 flex items-center justify-center rounded-full shadow-lg transition-transform active:scale-95 md:bottom-2 md:right-6"
          style={{ background: primary, color: onPrimary, width: 48, height: 48, bottom: "calc(80px + env(safe-area-inset-bottom, 0px))", right: 16 }}
        >
          <MessageCircle size={22} />
        </button>
      )}

      {/* Mobile: full screen panel */}
      {isOpen && (
        <div className="fixed z-50 flex flex-col md:hidden" style={{ background: bg, top: "15vh", left: 0, right: 0, bottom: 0 }}>
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 shrink-0 safe-top" style={{ borderBottom: `1px solid ${border}` }}>
            <span className="text-sm font-semibold" style={{ color: fg }}>Factory Assistant</span>
            <button onClick={() => setIsOpen(false)} className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ color: muted }} aria-label="Close">
              <X size={18} />
            </button>
          </div>

          {/* Messages */}
          <div ref={listRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
            {messages.length === 0 && <p className="py-8 text-center text-sm" style={{ color: muted }}>Ask me anything about production</p>}
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className="max-w-[80%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap"
                  style={{ background: m.role === "user" ? primary : alt, color: m.role === "user" ? onPrimary : fg }}
                >{m.text}</div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm" style={{ background: alt, color: muted }}>
                  <Loader2 size={14} className="animate-spin" /> Thinking...
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <form onSubmit={onSubmit} className="shrink-0 flex items-center gap-2 px-3 py-3" style={{ borderTop: `1px solid ${border}`, paddingBottom: "calc(12px + env(safe-area-inset-bottom, 0px))" }}>
            <input ref={inputRef} type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type a message..." disabled={loading}
              className="flex-1 min-w-0 rounded-lg px-3 py-2.5 text-sm focus:outline-none"
              style={{ border: `1px solid ${border}`, background: alt, color: fg }}
            />
            <button type="submit" disabled={loading || !input.trim()}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-opacity disabled:opacity-30"
              style={{ background: primary, color: onPrimary }}
            ><Send size={16} /></button>
          </form>
        </div>
      )}

      {/* Desktop: floating panel */}
      {isOpen && (
        <div className="hidden md:flex fixed z-50 flex-col w-[360px] h-[440px] rounded-xl border shadow-xl"
          style={{ background: bg, borderColor: border, bottom: 16, right: 24 }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 shrink-0" style={{ borderBottom: `1px solid ${border}` }}>
            <span className="text-sm font-semibold" style={{ color: fg }}>Factory Assistant</span>
            <button onClick={() => setIsOpen(false)} className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ color: muted }} aria-label="Close">
              <X size={18} />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
            {messages.length === 0 && <p className="py-8 text-center text-sm" style={{ color: muted }}>Ask me anything about production</p>}
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className="max-w-[80%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap"
                  style={{ background: m.role === "user" ? primary : alt, color: m.role === "user" ? onPrimary : fg }}
                >{m.text}</div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm" style={{ background: alt, color: muted }}>
                  <Loader2 size={14} className="animate-spin" /> Thinking...
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <form onSubmit={onSubmit} className="shrink-0 flex items-center gap-2 px-3 py-3" style={{ borderTop: `1px solid ${border}` }}>
            <input ref={inputRef} type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type a message..." disabled={loading}
              className="flex-1 min-w-0 rounded-lg px-3 py-2.5 text-sm focus:outline-none"
              style={{ border: `1px solid ${border}`, background: alt, color: fg }}
            />
            <button type="submit" disabled={loading || !input.trim()}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-opacity disabled:opacity-30"
              style={{ background: primary, color: onPrimary }}
            ><Send size={16} /></button>
          </form>
        </div>
      )}
    </>
  )
}
