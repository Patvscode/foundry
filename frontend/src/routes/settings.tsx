import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import { getHealth, getProviders, getRuntimeConfig, updateRuntimeConfig } from '@/api/client'

export function SettingsRoute() {
  const queryClient = useQueryClient()
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, retry: 1 })
  const providers = useQuery({ queryKey: ['providers'], queryFn: getProviders, retry: 1 })
  const runtimeConfig = useQuery({ queryKey: ['runtime-config'], queryFn: getRuntimeConfig, retry: 1 })

  // Local state for editable fields
  const [defaultProvider, setDefaultProvider] = useState('')
  const [defaultModel, setDefaultModel] = useState('')
  const [canExecute, setCanExecute] = useState(false)
  const [swarmMode, setSwarmMode] = useState('single')
  const [coordProvider, setCoordProvider] = useState('')
  const [coordModel, setCoordModel] = useState('')
  const [workerProvider, setWorkerProvider] = useState('')
  const [workerModel, setWorkerModel] = useState('')
  const [maxWorkers, setMaxWorkers] = useState(4)
  const [useCritic, setUseCritic] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saved' | 'error'>('idle')

  // Sync from server data
  useEffect(() => {
    if (providers.data) {
      setDefaultProvider(providers.data.active_provider)
      setDefaultModel(providers.data.active_model)
      setSwarmMode(providers.data.swarm?.mode || 'single')
      setCoordProvider(providers.data.swarm?.coordinator_provider || '')
      setCoordModel(providers.data.swarm?.coordinator_model || '')
      setWorkerProvider(providers.data.swarm?.worker_provider || '')
      setWorkerModel(providers.data.swarm?.worker_model || '')
      setMaxWorkers(providers.data.swarm?.max_workers || 4)
      setUseCritic(providers.data.swarm?.use_critic || false)
    }
  }, [providers.data])

  useEffect(() => {
    if (runtimeConfig.data) {
      const s = runtimeConfig.data.settings
      if (s['agent.can_execute'] !== undefined) setCanExecute(!!s['agent.can_execute'])
    }
  }, [runtimeConfig.data])

  const saveMut = useMutation({
    mutationFn: () => updateRuntimeConfig({
      'agent.default_provider': defaultProvider,
      'agent.default_model': defaultModel,
      'agent.can_execute': canExecute,
      'ingestion.swarm.mode': swarmMode,
      'ingestion.swarm.coordinator_provider': coordProvider,
      'ingestion.swarm.coordinator_model': coordModel,
      'ingestion.swarm.worker_provider': workerProvider,
      'ingestion.swarm.worker_model': workerModel,
      'ingestion.swarm.max_workers': maxWorkers,
      'ingestion.swarm.use_critic': useCritic,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] })
      queryClient.invalidateQueries({ queryKey: ['health'] })
      queryClient.invalidateQueries({ queryKey: ['runtime-config'] })
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    },
    onError: () => setSaveStatus('error'),
  })

  const connectedProviders = providers.data?.providers.filter(p => p.status === 'connected') || []
  const allProviders = providers.data?.providers.filter(p => p.id !== 'fallback') || []

  const modelsForProvider = (pid: string) => {
    const p = providers.data?.providers.find(pr => pr.id === pid)
    return p?.models || []
  }

  const STATUS_ICON: Record<string, string> = {
    connected: '✅', configured: '⚙️', always_available: '◻️',
    not_reachable: '❌', not_configured: '⬜',
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-zinc-100">Settings</h1>
        <button
          type="button"
          onClick={() => saveMut.mutate()}
          disabled={saveMut.isPending}
          className="rounded-md bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-400 disabled:opacity-50"
        >
          {saveMut.isPending ? 'Saving…' : saveStatus === 'saved' ? '✓ Saved' : 'Save All'}
        </button>
      </div>

      {/* Provider Selection */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 space-y-4">
        <h2 className="text-sm font-medium text-zinc-200">Default Provider & Model</h2>
        <p className="text-xs text-zinc-500">Used for ingestion analysis and agent chat. Changes take effect immediately after saving.</p>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-xs text-zinc-400">Provider</label>
            <select
              value={defaultProvider}
              onChange={(e) => { setDefaultProvider(e.target.value); setDefaultModel('') }}
              className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              {allProviders.map((p) => (
                <option key={p.id} value={p.id}>
                  {STATUS_ICON[p.status] || ''} {p.name}
                </option>
              ))}
              <option value="none">No provider (fallback)</option>
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs text-zinc-400">Model</label>
            <select
              value={defaultModel}
              onChange={(e) => setDefaultModel(e.target.value)}
              className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
            >
              <option value="">Auto-detect</option>
              {modelsForProvider(defaultProvider).map((m) => (
                <option key={typeof m === 'string' ? m : m.name} value={typeof m === 'string' ? m : m.name}>
                  {typeof m === 'string' ? m : m.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Provider status list */}
        <div className="space-y-1 pt-2">
          {providers.data?.providers.map((p) => (
            <div key={p.id} className="flex items-center justify-between text-xs">
              <span className="text-zinc-300">{STATUS_ICON[p.status] || ''} {p.name}</span>
              <span className="text-zinc-500">
                {p.status === 'connected' && p.models.length > 0
                  ? `${p.models.length} model${p.models.length > 1 ? 's' : ''}`
                  : p.status.replace(/_/g, ' ')}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Ingestion Swarm Config */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 space-y-4">
        <h2 className="text-sm font-medium text-zinc-200">Ingestion Mode</h2>
        <p className="text-xs text-zinc-500">Controls how Foundry analyzes research inputs. Swarm mode is for ingestion/discovery only.</p>

        <div className="space-y-2">
          <label className="flex cursor-pointer items-center gap-3 rounded-md border border-zinc-800 bg-zinc-950 p-3 hover:border-zinc-700">
            <input type="radio" name="swarm" value="single" checked={swarmMode === 'single'} onChange={() => setSwarmMode('single')} />
            <div>
              <div className="text-sm text-zinc-200">Single model</div>
              <div className="text-xs text-zinc-500">One model handles all analysis. Simple and reliable.</div>
            </div>
          </label>
          <label className="flex cursor-pointer items-center gap-3 rounded-md border border-zinc-800 bg-zinc-950 p-3 hover:border-zinc-700">
            <input type="radio" name="swarm" value="swarm" checked={swarmMode === 'swarm'} onChange={() => setSwarmMode('swarm')} />
            <div>
              <div className="text-sm text-zinc-200">Swarm (coordinator + workers)</div>
              <div className="text-xs text-zinc-500">Coordinator plans, workers execute in parallel, results synthesized.</div>
            </div>
          </label>
        </div>

        {swarmMode === 'swarm' && (
          <div className="space-y-3 rounded-md border border-zinc-800 bg-zinc-950 p-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-zinc-400">Coordinator provider</label>
                <select value={coordProvider} onChange={(e) => setCoordProvider(e.target.value)} className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-200">
                  <option value="">Same as default</option>
                  {connectedProviders.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400">Coordinator model</label>
                <select value={coordModel} onChange={(e) => setCoordModel(e.target.value)} className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-200">
                  <option value="">Auto</option>
                  {modelsForProvider(coordProvider || defaultProvider).map((m) => (
                    <option key={typeof m === 'string' ? m : m.name} value={typeof m === 'string' ? m : m.name}>{typeof m === 'string' ? m : m.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400">Worker provider</label>
                <select value={workerProvider} onChange={(e) => setWorkerProvider(e.target.value)} className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-200">
                  <option value="">Same as default</option>
                  {connectedProviders.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs text-zinc-400">Worker model</label>
                <select value={workerModel} onChange={(e) => setWorkerModel(e.target.value)} className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-200">
                  <option value="">Auto</option>
                  {modelsForProvider(workerProvider || defaultProvider).map((m) => (
                    <option key={typeof m === 'string' ? m : m.name} value={typeof m === 'string' ? m : m.name}>{typeof m === 'string' ? m : m.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div>
                <label className="text-xs text-zinc-400">Max workers</label>
                <input type="number" min={1} max={16} value={maxWorkers} onChange={(e) => setMaxWorkers(parseInt(e.target.value) || 4)} className="w-20 rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-200" />
              </div>
              <label className="flex items-center gap-2 text-xs text-zinc-400">
                <input type="checkbox" checked={useCritic} onChange={(e) => setUseCritic(e.target.checked)} />
                Enable critic/refinement pass
              </label>
            </div>
          </div>
        )}
      </section>

      {/* Execution */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 space-y-3">
        <h2 className="text-sm font-medium text-zinc-200">Shell Execution</h2>
        <label className="flex items-center gap-3">
          <input type="checkbox" checked={canExecute} onChange={(e) => setCanExecute(e.target.checked)} />
          <div>
            <span className="text-sm text-zinc-200">Enable workspace-scoped execution</span>
            <p className="text-xs text-zinc-500">Allows install, test, build, and shell commands inside subproject workspaces.</p>
          </div>
        </label>
      </section>

      {/* System info */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4 space-y-2">
        <h2 className="text-sm font-medium text-zinc-200">System</h2>
        {health.data && (
          <div className="grid grid-cols-2 gap-1 text-xs">
            <span className="text-zinc-500">Version</span><span className="text-zinc-300">{health.data.version}</span>
            <span className="text-zinc-500">Uptime</span><span className="text-zinc-300">{Math.floor(health.data.uptime_seconds / 60)} min</span>
            <span className="text-zinc-500">Database</span><span className="text-zinc-300">{health.data.db}</span>
            <span className="text-zinc-500">Disk free</span><span className="text-zinc-300">{health.data.disk_free_gb} GB</span>
          </div>
        )}
        <p className="text-xs text-zinc-600">Config file: ~/.foundry/config.toml · Runtime overrides saved to DB</p>
      </section>
    </div>
  )
}
