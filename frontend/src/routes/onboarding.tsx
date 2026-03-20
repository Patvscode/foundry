import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'

import { getProviders, updateRuntimeConfig, type ProviderInfo } from '@/api/client'

type Step = 'scan' | 'provider' | 'swarm' | 'done'

export function OnboardingRoute() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [step, setStep] = useState<Step>('scan')
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [swarmMode, setSwarmMode] = useState('single')
  const [coordinatorProvider, setCoordinatorProvider] = useState('')
  const [workerProvider, setWorkerProvider] = useState('')

  const providers = useQuery({
    queryKey: ['providers'],
    queryFn: getProviders,
    retry: 1,
  })

  const saveMut = useMutation({
    mutationFn: async () => {
      const settings: Record<string, unknown> = {
        'agent.default_provider': selectedProvider || 'none',
        'agent.default_model': selectedModel,
        'ingestion.swarm.mode': swarmMode,
        'setup.completed': true,
      }
      if (swarmMode === 'swarm') {
        settings['ingestion.swarm.coordinator_provider'] = coordinatorProvider || selectedProvider
        settings['ingestion.swarm.worker_provider'] = workerProvider || selectedProvider
        settings['ingestion.swarm.max_workers'] = 4
        settings['ingestion.swarm.use_critic'] = false
      }
      return updateRuntimeConfig(settings)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] })
      queryClient.invalidateQueries({ queryKey: ['health'] })
      setStep('done')
    },
  })

  const connectedProviders = providers.data?.providers.filter(
    (p) => p.status === 'connected' && p.id !== 'fallback'
  ) || []
  const allProviders = providers.data?.providers.filter((p) => p.id !== 'fallback') || []

  const availableModels = (() => {
    if (!selectedProvider || !providers.data) return []
    const p = providers.data.providers.find((pr) => pr.id === selectedProvider)
    return p?.models || []
  })()

  return (
    <div className="mx-auto flex min-h-[80vh] max-w-2xl flex-col items-center justify-center gap-6 px-4">
      <div className="w-full rounded-xl border border-zinc-800 bg-zinc-900 p-8">
        <h1 className="mb-2 text-xl font-semibold text-zinc-100">🔥 Welcome to Foundry</h1>
        <p className="mb-6 text-sm text-zinc-400">
          Let's get your research workspace connected to a local model.
        </p>

        {/* Step indicator */}
        <div className="mb-6 flex gap-2">
          {['scan', 'provider', 'swarm', 'done'].map((s) => (
            <div
              key={s}
              className={`h-1 flex-1 rounded-full ${
                s === step ? 'bg-blue-500' : step === 'done' || 
                (['scan','provider','swarm','done'].indexOf(s) < ['scan','provider','swarm','done'].indexOf(step)) 
                  ? 'bg-blue-500/30' : 'bg-zinc-800'
              }`}
            />
          ))}
        </div>

        {/* STEP 1: Scan */}
        {step === 'scan' && (
          <div className="space-y-4">
            <h2 className="text-sm font-medium text-zinc-200">Step 1: Scanning for providers…</h2>
            {providers.isLoading ? (
              <p className="text-sm text-zinc-500">Scanning local network for LLM providers…</p>
            ) : (
              <div className="space-y-2">
                {connectedProviders.length > 0 ? (
                  <>
                    <p className="text-sm text-emerald-400">
                      ✅ Found {connectedProviders.length} provider{connectedProviders.length > 1 ? 's' : ''}!
                    </p>
                    {connectedProviders.map((p) => (
                      <ProviderCard key={p.id} provider={p} />
                    ))}
                  </>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-amber-400">⚠ No local providers detected.</p>
                    <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3 text-xs text-zinc-400">
                      <p className="font-medium text-zinc-300 mb-1">To get started, try one of:</p>
                      <p>• <code>ollama serve</code> then <code>ollama pull qwen3.5:4b</code></p>
                      <p>• Start a llama.cpp server on port 18080</p>
                      <p>• Continue in fallback mode (synthetic placeholders)</p>
                    </div>
                  </div>
                )}
                {allProviders.filter(p => p.status !== 'connected').length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-zinc-500 mb-1">Not connected:</p>
                    {allProviders.filter(p => p.status !== 'connected').map((p) => (
                      <div key={p.id} className="text-xs text-zinc-600">
                        ❌ {p.name} — {p.requires}
                      </div>
                    ))}
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => setStep('provider')}
                  className="mt-4 rounded-md bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-400"
                >
                  Continue →
                </button>
              </div>
            )}
          </div>
        )}

        {/* STEP 2: Select provider + model */}
        {step === 'provider' && (
          <div className="space-y-4">
            <h2 className="text-sm font-medium text-zinc-200">Step 2: Choose your default provider & model</h2>
            <p className="text-xs text-zinc-500">This will be used for ingestion analysis and agent chat.</p>

            <div className="space-y-2">
              <label className="text-xs text-zinc-400">Provider</label>
              <select
                value={selectedProvider}
                onChange={(e) => { setSelectedProvider(e.target.value); setSelectedModel('') }}
                className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
              >
                <option value="">Select a provider…</option>
                {allProviders.map((p) => (
                  <option key={p.id} value={p.id} disabled={p.status === 'not_configured'}>
                    {p.name} {p.status === 'connected' ? '✅' : p.status === 'not_reachable' ? '❌' : '⚙️'}
                    {p.models.length > 0 ? ` (${p.models.length} models)` : ''}
                  </option>
                ))}
                <option value="none">No provider (fallback mode)</option>
              </select>
            </div>

            {availableModels.length > 0 && (
              <div className="space-y-2">
                <label className="text-xs text-zinc-400">Model</label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full rounded-md border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100"
                >
                  <option value="">Auto-detect</option>
                  {availableModels.map((m) => (
                    <option key={typeof m === 'string' ? m : m.name} value={typeof m === 'string' ? m : m.name}>
                      {typeof m === 'string' ? m : m.name}
                      {typeof m !== 'string' && m.size_gb ? ` (${m.size_gb} GB)` : ''}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {selectedProvider === 'none' && (
              <p className="text-xs text-amber-400">
                Fallback mode: ingestion will use synthetic placeholders. You can change this later in Settings.
              </p>
            )}

            <div className="flex gap-2 pt-2">
              <button type="button" onClick={() => setStep('scan')} className="rounded-md border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800">← Back</button>
              <button type="button" onClick={() => setStep('swarm')} className="rounded-md bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-400">Continue →</button>
            </div>
          </div>
        )}

        {/* STEP 3: Swarm mode */}
        {step === 'swarm' && (
          <div className="space-y-4">
            <h2 className="text-sm font-medium text-zinc-200">Step 3: Ingestion mode</h2>
            <p className="text-xs text-zinc-500">
              Choose how Foundry analyzes research inputs. Swarm mode uses a coordinator + specialist workers for deeper extraction.
            </p>

            <div className="space-y-2">
              <label className="flex cursor-pointer items-start gap-3 rounded-md border border-zinc-800 bg-zinc-950 p-3 hover:border-zinc-700">
                <input type="radio" name="swarm" value="single" checked={swarmMode === 'single'} onChange={() => setSwarmMode('single')} className="mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-zinc-200">Single model (default)</div>
                  <div className="text-xs text-zinc-500">One model handles all analysis. Simple, fast, reliable.</div>
                </div>
              </label>

              <label className="flex cursor-pointer items-start gap-3 rounded-md border border-zinc-800 bg-zinc-950 p-3 hover:border-zinc-700">
                <input type="radio" name="swarm" value="swarm" checked={swarmMode === 'swarm'} onChange={() => setSwarmMode('swarm')} className="mt-0.5" />
                <div>
                  <div className="text-sm font-medium text-zinc-200">Swarm (coordinator + workers)</div>
                  <div className="text-xs text-zinc-500">
                    A stronger coordinator plans the analysis, smaller workers execute in parallel, results are synthesized.
                    Best for complex research with multiple models available.
                  </div>
                </div>
              </label>
            </div>

            {swarmMode === 'swarm' && (
              <div className="space-y-3 rounded-md border border-zinc-800 bg-zinc-950 p-3">
                <p className="text-xs text-zinc-400">Swarm configuration (can be changed later in Settings)</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-zinc-500">Coordinator provider</label>
                    <select
                      value={coordinatorProvider}
                      onChange={(e) => setCoordinatorProvider(e.target.value)}
                      className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-200"
                    >
                      <option value="">Same as default</option>
                      {allProviders.filter(p => p.status === 'connected').map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-zinc-500">Worker provider</label>
                    <select
                      value={workerProvider}
                      onChange={(e) => setWorkerProvider(e.target.value)}
                      className="w-full rounded-md border border-zinc-700 bg-zinc-900 px-2 py-1.5 text-xs text-zinc-200"
                    >
                      <option value="">Same as default</option>
                      {allProviders.filter(p => p.status === 'connected').map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            <div className="flex gap-2 pt-2">
              <button type="button" onClick={() => setStep('provider')} className="rounded-md border border-zinc-700 px-4 py-2 text-sm text-zinc-300 hover:bg-zinc-800">← Back</button>
              <button type="button" onClick={() => saveMut.mutate()} disabled={saveMut.isPending} className="rounded-md bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-400 disabled:opacity-50">
                {saveMut.isPending ? 'Saving…' : 'Finish Setup ✓'}
              </button>
            </div>
          </div>
        )}

        {/* STEP 4: Done */}
        {step === 'done' && (
          <div className="space-y-4 text-center">
            <div className="text-4xl">🎉</div>
            <h2 className="text-lg font-medium text-zinc-100">Setup complete!</h2>
            <p className="text-sm text-zinc-400">
              Provider: <span className="text-zinc-200">{selectedProvider || 'fallback'}</span>
              {selectedModel && <> · Model: <span className="text-zinc-200">{selectedModel}</span></>}
              {' · '}Ingestion: <span className="text-zinc-200">{swarmMode}</span>
            </p>
            <p className="text-xs text-zinc-500">You can change these anytime in Settings.</p>
            <button
              type="button"
              onClick={() => navigate({ to: '/' })}
              className="rounded-md bg-blue-500 px-6 py-2 text-sm font-medium text-white hover:bg-blue-400"
            >
              Go to Dashboard →
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function ProviderCard({ provider }: { provider: ProviderInfo }) {
  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-200">{provider.name}</span>
        <span className="text-xs text-emerald-400">connected</span>
      </div>
      {provider.models.length > 0 && (
        <div className="mt-1 text-xs text-zinc-500">
          Models: {provider.models.slice(0, 5).map(m => typeof m === 'string' ? m : m.name).join(', ')}
          {provider.models.length > 5 && ` +${provider.models.length - 5} more`}
        </div>
      )}
    </div>
  )
}
