import clsx from 'clsx'

import { useAppStore, type AgentMode } from '@/stores/app'
import { AgentPanel } from '@/components/agent/AgentPanel'

const modes: Array<{ label: string; value: AgentMode }> = [
  { label: 'Explore', value: 'explore' },
  { label: 'Builder', value: 'builder' },
  { label: 'Full Override', value: 'full-override' },
]

interface AgentBarProps {
  projectId?: string
  resourceId?: string
  subprojectId?: string
}

export function AgentBar({ projectId, resourceId, subprojectId }: AgentBarProps) {
  const agentMode = useAppStore((s) => s.agentMode)
  const setAgentMode = useAppStore((s) => s.setAgentMode)
  const agentPanelOpen = useAppStore((s) => s.agentPanelOpen)
  const toggleAgentPanel = useAppStore((s) => s.toggleAgentPanel)

  return (
    <div className="flex flex-col">
      {/* Agent panel (slides up when expanded) */}
      {agentPanelOpen && (
        <AgentPanel
          projectId={projectId}
          resourceId={resourceId}
          subprojectId={subprojectId}
          expanded={agentPanelOpen}
        />
      )}

      {/* Bottom bar */}
      <div className="flex h-14 items-center gap-4 border-t border-zinc-800 bg-zinc-900 px-4">
        <div className="flex items-center gap-2 text-sm">
          {modes.map((mode) => {
            const active = mode.value === agentMode
            return (
              <button
                key={mode.value}
                type="button"
                onClick={() => setAgentMode(mode.value)}
                className={clsx(
                  'inline-flex items-center gap-2 rounded-md px-2 py-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50',
                  active ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200',
                )}
              >
                <span>{mode.label}</span>
                <span className={clsx('text-xs', active ? 'text-emerald-400' : 'text-zinc-500')}>
                  {active ? '●' : '○'}
                </span>
              </button>
            )
          })}
        </div>

        <button
          type="button"
          onClick={toggleAgentPanel}
          className={clsx(
            'ml-auto rounded-md border px-3 py-1 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50',
            agentPanelOpen
              ? 'border-blue-500/50 bg-blue-500/10 text-blue-300'
              : 'border-zinc-800 text-zinc-300 hover:bg-zinc-800 hover:text-zinc-100',
          )}
        >
          {agentPanelOpen ? '▼ Agent' : '▲ Agent'}
        </button>
      </div>
    </div>
  )
}
