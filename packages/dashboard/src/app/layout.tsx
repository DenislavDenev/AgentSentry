import type { Metadata } from "next"
import "./globals.css"
import { Sidebar } from "@/components/nav/Sidebar"

export const metadata: Metadata = {
  title: "AgentSentry",
  description: "Self-hosted observability for local AI coding agents",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="flex h-screen overflow-hidden bg-gray-950 text-gray-100 antialiased">
        <Sidebar />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </body>
    </html>
  )
}
