import type { Metadata } from 'next'

import './styles.css'

export const metadata: Metadata = {
  title: 'Evox | governed learning loop',
  description: 'Owner cockpit for governed agentic systems.',
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>
}
