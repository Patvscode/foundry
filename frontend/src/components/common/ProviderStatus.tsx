import { useQuery } from '@tanstack/react-query'
import { getProviders } from '@/api/client'

const STATUS_COLORS: Record<string, string> = {
  connected: 'text-green-400',
  configured: 'text-blue-400',
  always_available: 'text-zinc-400',
  not_reachable: 'text-red-400',
  not_configured: 'text-zinc-600',
}

const MODE_LABELS: Record<string, string> = {
  local: '🟢 Local Model',
  api: '🔵 API Provider',
  fallback: '🟡 Fallback Mode',
}

export function ProviderStatus({ compact = false }: { compact?: boolean }) {
  const { data, isLoading } = useQuery({
    queryKey: ['providers'],
    queryFn: getProviders,
    retry: 1,
    staleTime: 30_000,
  })

  if (isLoading) return <span className="text-xs text-zinc-500">Checking providers…</span>
  if (!data) return null

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-xs">
        <span className="text-zinc-400">{MODE_LABELS[data.mode] || data.mode}</span>
        {data.active_model && <span className="text-zinc-500">({data.active_model})</span>}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-300">LLM Providers</span>
        <span className="text-xs text-zinc-500">{MODE_LABELS[data.mode] || data.mode}</span>
      </div>

      {data.providers.map((p) => (
        <div key={p.id} className="flex items-center justify-between rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2">
          <div>
            <div className="text-sm text-zinc-200">{p.name}</div>
            {p.models.length > 0 && (
              <div className="text-xs text-zinc-500">
                {p.models.slice(0, 3).map((m) => (typeof m === 'string' ? m : m.name)).join(', ')}
                {p.models.length > 3 && ` +${p.models.length - 3} more`}
              </div>
            )}
          </div>
          <span className={`text-xs font-medium ${STATUS_COLORS[p.status] || 'text-zinc-500'}`}>
            {p.status.replace(/_/g, ' ')}
          </span>
        </div>
      ))}

      {data.setup_hint && (
        <p className="whitespace-pre-line text-xs text-zinc-500">{data.setup_hint}</p>
      )}
    </div>
  )
}
