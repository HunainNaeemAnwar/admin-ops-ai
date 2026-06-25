"use client"

import { useState, useEffect, useRef, type FormEvent } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
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

function MarkdownContent({ text }: { text: string }) {
  const safe = text.replace(/(\d+)\*(\d+)/g, "`$1*$2`")
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="my-1 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-4 my-1 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-4 my-1 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li>{children}</li>,
        strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
        code: ({ className, ...props }) => {
          const isInline = !className
          if (isInline) {
            return <code className="rounded px-1 py-0.5 text-xs" style={{ background: "rgba(128,128,128,0.2)" }} {...props} />
          }
          return <pre className="rounded-lg p-3 my-2 overflow-x-auto text-xs" style={{ background: "rgba(0,0,0,0.1)" }}><code {...props} /></pre>
        },
      }}
    >{safe}</ReactMarkdown>
  )
}

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => { setMessages(loadMessages()) }, [])
  useEffect(() => { saveMessages(messages) }, [messages])
  useEffect(() => { if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight }, [messages])
  useEffect(() => { if (isOpen) setTimeout(() => inputRef.current?.focus(), 100) }, [isOpen])

  useEffect(() => {
    return () => { abortRef.current?.abort() }
  }, [])

  const send = async (text: string) => {
    setMessages((p) => [...p, { id: crypto.randomUUID(), role: "user", text, timestamp: new Date() }])
    setInput(""); setLoading(true)

    const msgId = crypto.randomUUID()
    let accumulated = ""

    try {
      const c = new AbortController()
      abortRef.current = c
      const t = setTimeout(() => c.abort(), TIMEOUT_MS)

      const r = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || ""}/admin/chat/stream`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }), signal: c.signal,
      })
      clearTimeout(t)

      if (!r.ok) throw new ApiError("fail", r.status)

      setMessages((p) => [...p, { id: msgId, role: "assistant", text: "", timestamp: new Date() }])

      const reader = r.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() || ""

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue
          const data = line.slice(6)
          if (data === "[DONE]") break
          accumulated += data
          setMessages((p) => p.map((m) => m.id === msgId ? { ...m, text: accumulated } : m))
        }
      }
    } catch (e) {
      if (accumulated) return
      let t = "Cannot reach server"
      if (e instanceof ApiError) t = `Error ${e.status}`
      else if (e instanceof TypeError) t = "Backend offline"
      setMessages((p) => {
        if (p.some((m) => m.id === msgId)) return p.map((m) => m.id === msgId ? { ...m, text: t } : m)
        return [...p, { id: msgId, role: "assistant", text: t, timestamp: new Date() }]
      })
    } finally { setLoading(false); abortRef.current = null }
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
          className="fixed z-50 flex items-center justify-center rounded-full shadow-lg transition-transform active:scale-95 bottom-[calc(88px+env(safe-area-inset-bottom,0px))] md:bottom-3 md:right-6"
          style={{ background: primary, color: onPrimary, width: 48, height: 48, right: 16 }}
        >
          <MessageCircle size={22} />
        </button>
      )}

      {/* Mobile: full screen panel */}
      {isOpen && (
        <div className="fixed z-50 flex flex-col md:hidden" style={{ background: bg, top: "15vh", left: 0, right: 0, bottom: 0 }}>
          <div className="flex items-center justify-between px-4 py-3 shrink-0 safe-top" style={{ borderBottom: `1px solid ${border}` }}>
            <span className="text-sm font-semibold" style={{ color: fg }}>Factory Assistant</span>
            <button onClick={() => setIsOpen(false)} className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ color: muted }} aria-label="Close">
              <X size={18} />
            </button>
          </div>

          <div ref={listRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
            {messages.length === 0 && <p className="py-8 text-center text-sm" style={{ color: muted }}>Ask me anything about production</p>}
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                {m.role === "user" ? (
                  <div className="max-w-[80%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap"
                    style={{ background: primary, color: onPrimary }}
                  >{m.text}</div>
                ) : (
                  <div className="max-w-[80%] rounded-xl px-3 py-2 text-sm leading-relaxed [&_*]:my-0"
                    style={{ background: alt, color: fg }}
                  >
                    {m.text ? <MarkdownContent text={m.text} /> : null}
                  </div>
                )}
              </div>
            ))}
            {loading && !messages.some((m) => m.role === "assistant" && m.text === "" && messages.indexOf(m) === messages.length - 1) && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm" style={{ background: alt, color: muted }}>
                  <Loader2 size={14} className="animate-spin" /> Thinking...
                </div>
              </div>
            )}
          </div>

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
          <div className="flex items-center justify-between px-4 py-3 shrink-0" style={{ borderBottom: `1px solid ${border}` }}>
            <span className="text-sm font-semibold" style={{ color: fg }}>Factory Assistant</span>
            <button onClick={() => setIsOpen(false)} className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ color: muted }} aria-label="Close">
              <X size={18} />
            </button>
          </div>

          <div ref={listRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-3 min-h-0">
            {messages.length === 0 && <p className="py-8 text-center text-sm" style={{ color: muted }}>Ask me anything about production</p>}
            {messages.map((m) => (
              <div key={m.id} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                {m.role === "user" ? (
                  <div className="max-w-[80%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap"
                    style={{ background: primary, color: onPrimary }}
                  >{m.text}</div>
                ) : (
                  <div className="max-w-[80%] rounded-xl px-3 py-2 text-sm leading-relaxed [&_*]:my-0"
                    style={{ background: alt, color: fg }}
                  >
                    {m.text ? <MarkdownContent text={m.text} /> : null}
                  </div>
                )}
              </div>
            ))}
            {loading && !messages.some((m) => m.role === "assistant" && m.text === "" && messages.indexOf(m) === messages.length - 1) && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm" style={{ background: alt, color: muted }}>
                  <Loader2 size={14} className="animate-spin" /> Thinking...
                </div>
              </div>
            )}
          </div>

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
