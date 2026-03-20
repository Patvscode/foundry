import { type ReactNode } from 'react'

import { AgentBar } from '@/components/layout/AgentBar'
import { Sidebar } from '@/components/layout/Sidebar'
import { useAppStore } from '@/stores/app'

interface ShellProps {
  children: ReactNode
}

export function Shell({ children }: ShellProps) {
  const context = useAppStore((s) => s.agentContext)

  return (
    <div className="grid h-screen grid-rows-[1fr_auto] bg-zinc-950 text-zinc-100">
      <div className="grid min-h-0 grid-cols-[auto_1fr]">
        <Sidebar />
        <main className="min-h-0 overflow-auto bg-zinc-950 p-4">{children}</main>
      </div>
      <AgentBar
        projectId={context?.projectId}
        resourceId={context?.resourceId}
        subprojectId={context?.subprojectId}
      />
    </div>
  )
}
