import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { executeInSubproject, getEcosystem, getExecHistory, type ExecResponse } from '@/api/client'

interface Props {
  subprojectId: string
}

const ACTIONS = [
  { id: 'install', label: '📦 Install', desc: 'Install dependencies' },
  { id: 'test', label: '🧪 Test', desc: 'Run tests' },
  { id: 'build', label: '🔨 Build', desc: 'Build project' },
  { id: 'shell', label: '💻 Shell', desc: 'Custom command' },
]

export function ExecutionPanel({ subprojectId }: Props) {
  const queryClient = useQueryClient()
  const [customCmd, setCustomCmd] = useState('')
  const [lastResult, setLastResult] = useState<ExecResponse | null>(null)
  const [error, setError] = useState('')

  const ecosystem = useQuery({
    queryKey: ['ecosystem', subprojectId],
    queryFn: () => getEcosystem(subprojectId),
  })

  const history = useQuery({
    queryKey: ['exec-history', subprojectId],
    queryFn: () => getExecHistory(subprojectId),
  })

  const execMut = useMutation({
    mutationFn: ({ action, command }: { action: string; command: string }) =>
      executeInSubproject(subprojectId, action, command, 60),
    onSuccess: (data) => {
      setLastResult(data)
      setError('')
      queryClient.invalidateQueries({ queryKey: ['exec-history', subprojectId] })
    },
    onError: (err: Error) => {
      setError(err.message)
      setLastResult(null)
    },
  })

  const handleAction = (action: string) => {
    if (action === 'shell' && !customCmd.trim()) {
      setError('Enter a command first')
      return
    }
    setError('')
    execMut.mutate({ action, command: action === 'shell' ? customCmd : '' })
  }

  return (
    <div className="space-y-4">
      {/* Ecosystem info */}
      {ecosystem.data && (
        <div className="flex items-center gap-3 text-xs text-zinc-500">
          <span>Ecosystem: <span className="text-zinc-300">{ecosystem.data.ecosystem}</span></span>
          {ecosystem.data.workspace_exists
            ? <span className="text-emerald-400">✅ workspace exists</span>
            : <span className="text-red-400">❌ no workspace</span>}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        {ACTIONS.filter(a => a.id !== 'shell').map((a) => (
          <button
            key={a.id}
            type="button"
            onClick={() => handleAction(a.id)}
            disabled={execMut.isPending}
            className="rounded-md border border-zinc-700 bg-zinc-950 px-3 py-1.5 text-xs font-medium text-zinc-200 hover:border-zinc-600 hover:bg-zinc-900 disabled:opacity-50"
            title={a.desc}
          >
            {a.label}
          </button>
        ))}
      </div>

      {/* Custom command */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Custom command (e.g. ls -la, cat README.md)"
          value={customCmd}
          onChange={(e) => setCustomCmd(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAction('shell')}
          className="h-8 flex-1 rounded-md border border-zinc-700 bg-zinc-950 px-3 text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
        />
        <button
          type="button"
          onClick={() => handleAction('shell')}
          disabled={execMut.isPending || !customCmd.trim()}
          className="rounded-md bg-zinc-700 px-3 py-1 text-xs text-zinc-200 hover:bg-zinc-600 disabled:opacity-50"
        >
          Run
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-400">
          {error.includes('403') ? '⚠ Execution is disabled. Enable it in Settings → Shell Execution.' : error}
        </div>
      )}

      {/* Running indicator */}
      {execMut.isPending && (
        <div className="flex items-center gap-2 text-xs text-zinc-400">
          <span className="animate-pulse">⏳</span> Running…
        </div>
      )}

      {/* Last result */}
      {lastResult && (
        <div className="space-y-2">
          <div className="flex items-center gap-3 text-xs">
            <span className={lastResult.exit_code === 0 ? 'text-emerald-400' : 'text-red-400'}>
              {lastResult.exit_code === 0 ? '✅' : '❌'} exit {lastResult.exit_code}
            </span>
            <span className="text-zinc-500">{lastResult.duration_ms}ms</span>
            <span className="text-zinc-600">{lastResult.command}</span>
            {lastResult.timed_out && <span className="text-amber-400">⏰ timed out</span>}
          </div>
          {lastResult.stdout && (
            <pre className="max-h-60 overflow-auto rounded-md border border-zinc-800 bg-zinc-950 p-2 text-xs text-zinc-300">
              {lastResult.stdout}
            </pre>
          )}
          {lastResult.stderr && (
            <pre className="max-h-40 overflow-auto rounded-md border border-red-500/20 bg-zinc-950 p-2 text-xs text-red-300">
              {lastResult.stderr}
            </pre>
          )}
        </div>
      )}

      {/* History */}
      {history.data && history.data.length > 0 && (
        <div>
          <h3 className="mb-2 text-xs uppercase tracking-wide text-zinc-500">Recent executions</h3>
          <div className="space-y-1">
            {history.data.slice(0, 10).map((h) => (
              <div key={h.id} className="flex items-center gap-3 text-xs">
                <span className={h.exit_code === 0 ? 'text-emerald-400' : 'text-red-400'}>
                  {h.exit_code === 0 ? '✓' : '✗'}
                </span>
                <span className="flex-1 truncate text-zinc-400" title={h.command}>{h.command}</span>
                <span className="text-zinc-600">{h.duration_ms}ms</span>
                <span className="text-zinc-700">{h.action_type}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
