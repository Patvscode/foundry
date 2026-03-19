import { useQuery } from '@tanstack/react-query'

import { getHealth } from '@/api/client'
import { StatusBadge } from '@/components/common/StatusBadge'

export function DashboardRoute() {
  const { data, error, isPending } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    retry: 1,
  })

  return (
    <div className="mx-auto flex h-full w-full max-w-4xl flex-col gap-4">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="text-sm font-medium text-zinc-300">System Status</h2>
        <div className="mt-3">
          {isPending ? (
            <span className="text-sm text-zinc-400">Checking backend health...</span>
          ) : error ? (
            <div className="space-y-2">
              <StatusBadge status="error" label="Backend unreachable" />
              <p className="text-sm text-zinc-400">Could not connect to `/api/system/health`.</p>
            </div>
          ) : data ? (
            <div className="space-y-2">
              <StatusBadge status={data.status === 'healthy' ? 'healthy' : 'degraded'} label={data.status} />
              <p className="text-sm text-zinc-400">Version {data.version} • DB {data.db} • Workspace {data.workspace}</p>
            </div>
          ) : null}
        </div>
      </section>

      <section className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-zinc-800 bg-zinc-900 p-8">
        <div className="max-w-lg space-y-3 text-center">
          <h1 className="text-2xl font-semibold text-zinc-100">🔥 No projects yet</h1>
          <p className="text-zinc-400">Paste a YouTube URL, drop a PDF, or link a repo.</p>
          <p className="text-zinc-400">Foundry will find the projects hiding inside.</p>
          <button
            type="button"
            className="mt-2 rounded-md bg-blue-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
          >
            New Project
          </button>
        </div>
      </section>
    </div>
  )
}
