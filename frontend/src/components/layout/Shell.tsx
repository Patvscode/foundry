import { type ReactNode } from 'react'

import { AgentBar } from '@/components/layout/AgentBar'
import { Sidebar } from '@/components/layout/Sidebar'

interface ShellProps {
  children: ReactNode
}

export function Shell({ children }: ShellProps) {
  return (
    <div className="grid h-screen grid-rows-[1fr_auto] bg-zinc-950 text-zinc-100">
      <div className="grid min-h-0 grid-cols-[auto_1fr]">
        <Sidebar />
        <main className="min-h-0 overflow-auto bg-zinc-950 p-4">{children}</main>
      </div>
      <AgentBar />
    </div>
  )
}
