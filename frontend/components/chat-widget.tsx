"use client"

import { useState, useEffect, useRef, useCallback, type FormEvent } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { ApiError } from "@/lib/api"
import type { ChatMessage } from "@/lib/types"
import { MessageCircle, X, Send, Loader2, History, Trash2 } from "lucide-react"

const MSG_KEY = "admin-chat-messages"
const SESSION_KEY = "admin-chat-sid"
const TIMEOUT_MS = 120_000

function getSid(): string {
  if (typeof window === "undefined") return "default"
  let sid = localStorage.getItem(SESSION_KEY)
  if (!sid) {
    sid = crypto.randomUUID()
    localStorage.setItem(SESSION_KEY, sid)
  }
  return sid
}

function setSid(sid: string) {
  localStorage.setItem(SESSION_KEY, sid)
}

function loadLocalMessages(): ChatMessage[] {
  if (typeof window === "undefined") return []
  try {
    const raw = sessionStorage.getItem(MSG_KEY)
    if (!raw) return []
    return JSON.parse(raw).map((m: ChatMessage) => ({ ...m, timestamp: new Date(m.timestamp) }))
  } catch { return [] }
}

function saveLocalMessages(msgs: ChatMessage[]) {
  try { sessionStorage.setItem(MSG_KEY, JSON.stringify(msgs)) } catch {}
}

function MarkdownContent({ text }: { text: string }) {
  const safe = String(text ?? "").replace(/(\d+)\*(\d+)/g, "`$1*$2`")
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

interface SessionSummary {
  session_id: string
  preview: string
  created_at: string
  last_activity: string
  message_count: number
}

type PanelView = "chat" | "history"

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [view, setView] = useState<PanelView>("chat")
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  // init: load local messages + fetch remote history for saved sid
  useEffect(() => {
    const local = loadLocalMessages()
    const sid = getSid()
    if (local.length > 0) {
      setMessages(local)
    } else if (sid !== "default") {
      fetch(`/admin/chat/sessions/${sid}`, { credentials: "include" })
        .then((r) => r.ok ? r.json() : [])
        .then((data: { role: string; content: string }[]) => {
          if (data.length > 0) {
            const restored: ChatMessage[] = data.map((m, i) => ({
              id: `hist-${i}`,
              role: m.role as "user" | "assistant",
              text: m.content,
              timestamp: new Date(),
            }))
            setMessages(restored)
            saveLocalMessages(restored)
          }
        })
        .catch(() => {})
    }
  }, [])

  useEffect(() => { saveLocalMessages(messages) }, [messages])
  useEffect(() => { if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight }, [messages])
  useEffect(() => { if (isOpen && view === "chat") setTimeout(() => inputRef.current?.focus(), 100) }, [isOpen, view])

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

      const r = await fetch(`/admin/chat/stream`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, session_id: getSid() }), signal: c.signal,
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

  const openHistory = useCallback(async () => {
    setView("history")
    setSessionsLoading(true)
    try {
      const r = await fetch(`/admin/chat/sessions`, { credentials: "include" })
      if (r.ok) setSessions(await r.json())
    } catch {} finally { setSessionsLoading(false) }
  }, [])

  const loadSession = useCallback(async (sid: string) => {
    const oldSid = getSid()
    setSid(sid)
    setLoading(true)
    try {
      // Clear backend cache for old session to prevent stale context
      if (oldSid !== sid && oldSid !== "default") {
        fetch(`/admin/chat/sessions/${oldSid}/forget`, { method: "POST", credentials: "include" }).catch(() => {})
      }
      const r = await fetch(`/admin/chat/sessions/${sid}`, { credentials: "include" })
      if (r.ok) {
        const data: { role: string; content: string }[] = await r.json()
        const restored: ChatMessage[] = data.map((m, i) => ({
          id: `hist-${i}`,
          role: m.role as "user" | "assistant",
          text: m.content,
          timestamp: new Date(),
        }))
        setMessages(restored)
        saveLocalMessages(restored)
      }
    } catch {} finally { setLoading(false); setView("chat") }
  }, [])

  const newSession = useCallback(() => {
    const sid = crypto.randomUUID()
    setSid(sid)
    setMessages([])
    saveLocalMessages([])
    setView("chat")
  }, [])

  const deleteSession = useCallback(async (sid: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await fetch(`/admin/chat/sessions/${sid}`, {
        method: "DELETE", credentials: "include",
      })
      setSessions((p) => p.filter((s) => s.session_id !== sid))
      if (sid === getSid()) {
        const nsid = crypto.randomUUID()
        setSid(nsid)
        setMessages([])
        saveLocalMessages([])
      }
    } catch {}
  }, [])

  const close = useCallback(() => { setIsOpen(false); setView("chat") }, [])

  const bg = "var(--color-surface)"
  const border = "var(--color-border)"
  const fg = "var(--color-foreground)"
  const muted = "var(--color-muted)"
  const alt = "var(--color-surface-alt)"
  const primary = "var(--color-primary)"
  const onPrimary = "var(--color-on-primary)"
  const danger = "#dc2626"

  const header = (
    <div className="flex items-center justify-between px-4 py-3 shrink-0" style={{ borderBottom: `1px solid ${border}` }}>
      <span className="text-sm font-semibold" style={{ color: fg }}>
        {view === "chat" ? "Factory Assistant" : "Chat History"}
      </span>
      <div className="flex items-center gap-1">
        {view === "chat" ? (
          <button onClick={openHistory} className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ color: muted }} title="History">
            <History size={16} />
          </button>
        ) : (
          <button onClick={() => setView("chat")} className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ color: primary }} title="Back">
            <span className="text-sm font-medium">&larr;</span>
          </button>
        )}
        {view === "chat" && (
          <button onClick={close} className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ color: muted }} aria-label="Close">
            <X size={18} />
          </button>
        )}
        {view === "history" && (
          <button onClick={close} className="flex h-8 w-8 items-center justify-center rounded-lg" style={{ color: muted }} aria-label="Close">
            <X size={18} />
          </button>
        )}
      </div>
    </div>
  )

  const chatPanel = (
    <>
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

      <form onSubmit={onSubmit} className="shrink-0 flex items-center gap-2 px-3 py-3"
        style={{ borderTop: `1px solid ${border}`, paddingBottom: "calc(12px + env(safe-area-inset-bottom, 0px))" }}
      >
        <input ref={inputRef} type="text" value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..." disabled={loading}
          className="flex-1 min-w-0 rounded-lg px-3 py-2.5 text-sm focus:outline-none"
          style={{ border: `1px solid ${border}`, background: alt, color: fg }}
        />
        <button type="submit" disabled={loading || !input.trim()}
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg transition-opacity disabled:opacity-30"
          style={{ background: primary, color: onPrimary }}
        ><Send size={16} /></button>
      </form>
    </>
  )

  const historyPanel = (
    <div className="flex-1 overflow-y-auto px-4 py-3 min-h-0 space-y-1">
      <button onClick={newSession}
        className="w-full rounded-lg px-3 py-2.5 text-sm text-left font-medium mb-2"
        style={{ background: primary, color: onPrimary }}
      >
        + New Chat
      </button>
      {sessionsLoading ? (
        <div className="flex justify-center py-8"><Loader2 size={16} className="animate-spin" style={{ color: muted }} /></div>
      ) : sessions.length === 0 ? (
        <p className="py-8 text-center text-sm" style={{ color: muted }}>No past sessions</p>
      ) : (
        sessions.map((s) => {
          const isActive = s.session_id === getSid()
          const date = s.created_at ? new Date(s.created_at + "Z") : new Date()
          const label = date.toLocaleDateString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
          return (
            <button key={s.session_id} onClick={() => loadSession(s.session_id)}
              className="w-full rounded-lg px-3 py-2 text-left text-sm flex items-start gap-2 transition-colors"
              style={{
                background: isActive ? alt : "transparent",
                color: fg,
              }}
            >
              <div className="flex-1 min-w-0">
                <div className="truncate font-medium">{s.preview || "New conversation"}</div>
                <div className="text-xs mt-0.5" style={{ color: muted }}>
                  {label} &middot; {s.message_count} messages
                </div>
              </div>
              <span onClick={(e) => deleteSession(s.session_id, e)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") deleteSession(s.session_id, e as unknown as React.MouseEvent) }}
                role="button" tabIndex={0}
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded cursor-pointer hover:bg-red-50 transition-colors"
                style={{ color: muted }}
                title="Delete"
              >
                <Trash2 size={14} />
              </span>
            </button>
          )
        })
      )}
    </div>
  )

  const panelContent = view === "chat" ? chatPanel : historyPanel

  return (
    <>
      {!isOpen && (
        <button onClick={() => setIsOpen(true)} aria-label="Open chat"
          className="fixed z-50 flex items-center justify-center rounded-full shadow-lg transition-transform active:scale-95 bottom-[calc(88px+env(safe-area-inset-bottom,0px))] md:bottom-3 md:right-6"
          style={{ background: primary, color: onPrimary, width: 48, height: 48, right: 16 }}
        >
          <MessageCircle size={22} />
        </button>
      )}

      {isOpen && (
        <div className="fixed z-50 flex flex-col md:hidden" style={{ background: bg, top: "15vh", left: 0, right: 0, bottom: 0 }}>
          {header}
          {panelContent}
        </div>
      )}

      {isOpen && (
        <div className="hidden md:flex fixed z-50 flex-col w-[360px] h-[480px] rounded-xl border shadow-xl"
          style={{ background: bg, borderColor: border, bottom: 16, right: 24 }}
        >
          {header}
          {panelContent}
        </div>
      )}
    </>
  )
}
