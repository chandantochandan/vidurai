import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  metadataBase: new URL('https://vidurai.ai'),
  title: 'Vidurai — The Human–AI Context Layer',
  description: 'A local, intelligent mediator between you and every AI. Vidurai watches your work, understands your intent, forgets the noise, and whispers exactly the right context to any AI — instantly.',
  keywords: ['Vidurai', 'AI context layer', 'developer tools', 'AI productivity', 'terminal context', 'local AI mediator', 'context management', 'AI assistance'],
  authors: [{ name: 'Chandan' }],
  icons: {
    icon: '/favicon.ico',
    shortcut: '/favicon.ico',
    apple: '/kosha-icon.png',
  },
  openGraph: {
    title: 'Vidurai — The Human–AI Context Layer',
    description: 'A local, intelligent mediator between you and every AI. Strategic forgetting for smarter context.',
    type: 'website',
    url: 'https://vidurai.ai',
    siteName: 'Vidurai',
    images: [
      {
        url: '/logo.jpg',
        width: 1200,
        height: 630,
        alt: 'Vidurai - The Human–AI Context Layer',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Vidurai — The Human–AI Context Layer',
    description: 'A local, intelligent mediator between you and every AI. Strategic forgetting for smarter context.',
    images: ['/logo.jpg'],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-black text-slate-100 min-h-screen">
        {children}
      </body>
    </html>
  )
}
