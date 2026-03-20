import { useQuery } from '@tanstack/react-query'
import { getConfig, getHealth } from '@/api/client'
import { ProviderStatus } from '@/components/common/ProviderStatus'

export function SettingsRoute() {
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, retry: 1 })
  const config = useQuery({ queryKey: ['config'], queryFn: getConfig, retry: 1 })

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <h1 className="text-lg font-semibold text-zinc-100">Settings</h1>

      {/* Provider Status */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <ProviderStatus />
      </section>

      {/* System Info */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-zinc-300">System</h2>
        {health.data && (
          <div className="space-y-1 text-sm text-zinc-400">
            <p>Version: {health.data.version}</p>
            <p>Uptime: {Math.floor(health.data.uptime_seconds / 60)} min</p>
            <p>Database: {health.data.db}</p>
            <p>Disk free: {health.data.disk_free_gb} GB</p>
            <p>Execution: {(health.data as unknown as Record<string, unknown>).execution_enabled ? '✅ Enabled' : '❌ Disabled'}</p>
          </div>
        )}
      </section>

      {/* Configuration */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="mb-3 text-sm font-medium text-zinc-300">Configuration</h2>
        <p className="mb-2 text-xs text-zinc-500">Edit ~/.foundry/config.toml to change settings. Restart after changes.</p>
        {config.data && (
          <pre className="max-h-96 overflow-auto rounded-md bg-zinc-950 p-3 text-xs text-zinc-400">
            {JSON.stringify(config.data, null, 2)}
          </pre>
        )}
      </section>
    </div>
  )
}
