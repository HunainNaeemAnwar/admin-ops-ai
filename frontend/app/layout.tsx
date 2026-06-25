import type { Metadata, Viewport } from "next"
import { Plus_Jakarta_Sans } from "next/font/google"
import "./globals.css"
import { Providers } from "@/providers"

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-jakarta",
})

export const metadata: Metadata = {
  title: "Admin Ops — Factory Production Dashboard",
  description: "Factory piece-rate worker tracking system",
}

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`light ${jakarta.variable}`} suppressHydrationWarning>
      <body className={jakarta.className} style={{ background: "var(--color-bg)", color: "var(--color-foreground)" }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
