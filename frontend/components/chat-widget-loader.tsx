"use client"

import dynamic from "next/dynamic"
import { useAuth } from "@/lib/auth"

const ChatWidgetInner = dynamic(
  () => import("@/components/chat-widget").then((mod) => ({ default: mod.ChatWidget })),
  { ssr: false }
)

export function ChatWidgetLoader() {
  const { user } = useAuth()

  if (!user?.is_father) return null

  return <ChatWidgetInner />
}
