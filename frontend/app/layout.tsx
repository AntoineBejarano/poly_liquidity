import './globals.css'
import { Providers } from './providers'
import { Toaster } from '@/components/ui/sonner'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'PolyLiquidity Desk — AI Desk for Betting & Trading',
  description: 'Trading algorítmico automatizado. Estrategias Polymarket, surebets, liquidez near-resolution y tips de Telegram.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  )
}

