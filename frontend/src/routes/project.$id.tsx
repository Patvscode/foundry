import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { addResource, getProject, getResource, getResources, type Resource } from '@/api/client'
import { StatusBadge } from '@/components/common/StatusBadge'
import { ResourceCard } from '@/components/resource/ResourceCard'

interface ProjectWorkspaceRouteProps {
  id: string
}

// Coarse statuses that indicate active processing
const ACTIVE_COARSE = new Set(['pending', 'processing'])

export function ProjectWorkspaceRoute({ id }: ProjectWorkspaceRouteProps) {
  const queryClient = useQueryClient()
  const [selectedResourceId, setSelectedResourceId] = useState<string | null>(null)
  const [newUrl, setNewUrl] = useState('')
  const [urlError, setUrlError] = useState('')

  // Fetch project
  const { data: project, isPending, error } = useQuery({
    queryKey: ['project', id],
    queryFn: () => getProject(id),
  })

  // Fetch resources — poll every 3s if any are actively processing
  const resources = useQuery({
    queryKey: ['resources', id],
    queryFn: () => getResources(id),
    refetchInterval: (query) => {
      const data = query.state.data
      if (data?.some((r: Resource) => ACTIVE_COARSE.has(r.status))) {
        return 3000
      }
      return false
    },
  })

  // Fetch selected resource detail (with extraction result)
  const selectedResource = useQuery({
    queryKey: ['resource', selectedResourceId],
    queryFn: () => (selectedResourceId ? getResource(selectedResourceId) : Promise.reject()),
    enabled: !!selectedResourceId,
    refetchInterval: (query) => {
      const data = query.state.data
      if (data && ACTIVE_COARSE.has(data.status)) {
        return 3000
      }
      return false
    },
  })

  // Add resource mutation
  const addMutation = useMutation({
    mutationFn: (url: string) => addResource(id, url),
    onSuccess: async (resource) => {
      await queryClient.invalidateQueries({ queryKey: ['resources', id] })
      setSelectedResourceId(resource.id)
      setNewUrl('')
    },
    onError: () => {
      setUrlError('Failed to add resource.')
    },
  })

  const handleAddResource = () => {
    const trimmed = newUrl.trim()
    if (!trimmed) {
      setUrlError('URL is required')
      return
    }
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      setUrlError('URL must start with http:// or https://')
      return
    }
    setUrlError('')
    addMutation.mutate(trimmed)
  }

  if (isPending) {
    return <div className="p-8 text-sm text-zinc-400">Loading project…</div>
  }
  if (error || !project) {
    return (
      <div className="p-8">
        <StatusBadge status="error" label="Project not found" />
      </div>
    )
  }

  const sel = selectedResource.data
  const proposals = sel?.extraction?.discovered_projects

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Project header */}
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h1 className="text-lg font-semibold text-zinc-100">{project.name}</h1>
        {project.description && <p className="mt-1 text-sm text-zinc-400">{project.description}</p>}
      </div>

      {/* Three-panel workspace */}
      <div className="grid min-h-0 flex-1 grid-cols-[280px_1fr_300px] gap-4">
        {/* Left: Resources */}
        <section className="flex flex-col gap-3 overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-xs uppercase tracking-wide text-zinc-500">Resources</h2>

          {/* Add resource input */}
          <div className="space-y-1">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Paste a URL…"
                value={newUrl}
                onChange={(e) => { setNewUrl(e.target.value); if (urlError) setUrlError('') }}
                onKeyDown={(e) => e.key === 'Enter' && handleAddResource()}
                className={`h-8 flex-1 rounded-md border bg-zinc-950 px-2 text-xs text-zinc-100 placeholder:text-zinc-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50 ${
                  urlError ? 'border-red-500' : 'border-zinc-800'
                }`}
              />
              <button
                type="button"
                onClick={handleAddResource}
                disabled={addMutation.isPending}
                className="rounded-md bg-blue-500 px-2 py-1 text-xs font-medium text-white transition-colors hover:bg-blue-400 disabled:opacity-50"
              >
                Add
              </button>
            </div>
            {urlError && <p className="text-xs text-red-400">{urlError}</p>}
          </div>

          {/* Resource list */}
          <div className="flex flex-1 flex-col gap-2">
            {resources.data?.length ? (
              resources.data.map((r) => (
                <ResourceCard
                  key={r.id}
                  resource={r}
                  selected={r.id === selectedResourceId}
                  onClick={() => setSelectedResourceId(r.id)}
                />
              ))
            ) : (
              <p className="text-sm text-zinc-400">No resources yet. Add a URL to get started.</p>
            )}
          </div>
        </section>

        {/* Center: Resource detail */}
        <section className="overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          {sel ? (
            <div className="space-y-4">
              <div>
                <h2 className="text-sm font-medium text-zinc-200">{sel.title || sel.url}</h2>
                <p className="mt-1 text-xs text-zinc-500">{sel.url}</p>
              </div>

              {sel.pipeline_error && (
                <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3">
                  <p className="text-sm text-red-400">{sel.pipeline_error}</p>
                </div>
              )}

              {sel.extraction?.summary && (
                <div>
                  <h3 className="text-xs uppercase tracking-wide text-zinc-500">Summary</h3>
                  <p className="mt-2 text-sm leading-relaxed text-zinc-300">
                    {sel.extraction.summary}
                  </p>
                  {sel.extraction.model_used === 'fallback' && (
                    <p className="mt-1 text-xs text-amber-400">
                      ⚠ Placeholder result — no LLM provider was available
                    </p>
                  )}
                </div>
              )}

              {sel.extraction?.key_concepts && sel.extraction.key_concepts.length > 0 && (
                <div>
                  <h3 className="text-xs uppercase tracking-wide text-zinc-500">Key Concepts</h3>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {sel.extraction.key_concepts.map((c, i) => (
                      <span key={i} className="rounded-full border border-zinc-700 bg-zinc-800 px-2 py-0.5 text-xs text-zinc-300">
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {sel.extraction?.open_questions && sel.extraction.open_questions.length > 0 && (
                <div>
                  <h3 className="text-xs uppercase tracking-wide text-zinc-500">Open Questions</h3>
                  <ul className="mt-2 space-y-1">
                    {sel.extraction.open_questions.map((q, i) => (
                      <li key={i} className="text-sm text-zinc-400">• {q}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-full items-center justify-center">
              <p className="text-sm text-zinc-500">Select a resource to see details</p>
            </div>
          )}
        </section>

        {/* Right: Discovered proposals */}
        <section className="overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-xs uppercase tracking-wide text-zinc-500">Discovered Projects</h2>
          {proposals && proposals.length > 0 ? (
            <div className="mt-3 space-y-3">
              {proposals.map((p, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-zinc-800 bg-zinc-950 p-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-zinc-200">{p.suggested_name}</span>
                    <span className={`text-xs ${p.confidence >= 0.7 ? 'text-emerald-400' : p.confidence >= 0.3 ? 'text-amber-400' : 'text-zinc-500'}`}>
                      {Math.round(p.confidence * 100)}%
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-zinc-400">{p.description}</p>
                  {p.is_synthetic && (
                    <p className="mt-1 text-xs text-amber-400">⚠ Placeholder — no LLM available</p>
                  )}
                  <div className="mt-2 flex items-center gap-2">
                    <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-xs text-zinc-400">
                      {p.type}
                    </span>
                    <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-xs text-zinc-400">
                      {p.complexity}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : sel && sel.pipeline_status === 'discovered' ? (
            <p className="mt-3 text-sm text-zinc-400">No projects discovered in this resource.</p>
          ) : sel ? (
            <p className="mt-3 text-sm text-zinc-400">Waiting for analysis to complete…</p>
          ) : (
            <p className="mt-3 text-sm text-zinc-400">Select a resource to see proposals.</p>
          )}
        </section>
      </div>
    </div>
  )
}
