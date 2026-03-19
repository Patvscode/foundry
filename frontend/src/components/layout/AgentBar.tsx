import clsx from 'clsx'

import { useAppStore, type AgentMode } from '@/stores/app'

const modes: Array<{ label: string; value: AgentMode }> = [
  { label: 'Explore', value: 'explore' },
  { label: 'Builder', value: 'builder' },
  { label: 'Full Override', value: 'full-override' },
]

export function AgentBar() {
  const agentMode = useAppStore((state) => state.agentMode)
  const setAgentMode = useAppStore((state) => state.setAgentMode)
  const toggleAgentPanel = useAppStore((state) => state.toggleAgentPanel)

  return (
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
              <span className={clsx('text-xs', active ? 'text-emerald-400' : 'text-zinc-500')}>{active ? '●' : '○'}</span>
            </button>
          )
        })}
      </div>

      <input
        type="text"
        placeholder="Ask something..."
        className="h-9 flex-1 rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
      />

      <button
        type="button"
        onClick={toggleAgentPanel}
        className="rounded-md border border-zinc-800 px-3 py-1 text-sm text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
        aria-label="Expand agent panel"
      >
        ▲
      </button>
    </div>
  )
}
