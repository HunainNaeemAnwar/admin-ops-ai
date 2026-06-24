import type { Metadata, Viewport } from "next"
import { Inter } from "next/font/google"
import "./globals.css"
import { Providers } from "@/providers"

const inter = Inter({ subsets: ["latin"] })

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
    <html lang="en" className="light" suppressHydrationWarning>
      <body className={`${inter.className} antialiased`} style={{ background: "var(--color-bg)", color: "var(--color-foreground)" }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
