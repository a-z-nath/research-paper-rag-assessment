import './globals.css'
import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Research Paper RAG System',
  description: 'Query and manage research papers with AI',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <nav className="bg-gray-800 text-white p-4">
          <div className="container mx-auto flex gap-6">
            <Link href="/" className="hover:text-blue-300">
              Home
            </Link>
            <Link href="/upload" className="hover:text-blue-300">
              Upload Papers
            </Link>
            <Link href="/papers" className="hover:text-blue-300">
              All Papers
            </Link>
            <Link href="/query" className="hover:text-blue-300">
              Query Papers
            </Link>
            <Link href="/history" className="hover:text-blue-300">
              Query History
            </Link>
          </div>
        </nav>
        <main className="container mx-auto p-6">
          {children}
        </main>
      </body>
    </html>
  )
}
