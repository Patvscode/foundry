import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Folder } from 'lucide-react'
import { useState } from 'react'

import {
  acceptProposal,
  addResource,
  getProject,
  getResource,
  getResources,
  getSubprojects,
  rejectProposal,
  type Resource,
} from '@/api/client'
import { StatusBadge } from '@/components/common/StatusBadge'
import { ProposalCard } from '@/components/resource/ProposalCard'
import { ResourceCard } from '@/components/resource/ResourceCard'

interface ProjectWorkspaceRouteProps {
  id: string
}

const ACTIVE_COARSE = new Set(['pending', 'processing'])

export function ProjectWorkspaceRoute({ id }: ProjectWorkspaceRouteProps) {
  const queryClient = useQueryClient()
  const [selectedResourceId, setSelectedResourceId] = useState<string | null>(null)
  const [newUrl, setNewUrl] = useState('')
  const [urlError, setUrlError] = useState('')

  const { data: project, isPending, error } = useQuery({
    queryKey: ['project', id],
    queryFn: () => getProject(id),
  })

  const resources = useQuery({
    queryKey: ['resources', id],
    queryFn: () => getResources(id),
    refetchInterval: (query) => {
      const data = query.state.data
      if (data?.some((r: Resource) => ACTIVE_COARSE.has(r.status))) return 3000
      return false
    },
  })

  const selectedResource = useQuery({
    queryKey: ['resource', selectedResourceId],
    queryFn: () => (selectedResourceId ? getResource(selectedResourceId) : Promise.reject()),
    enabled: !!selectedResourceId,
    refetchInterval: (query) => {
      const data = query.state.data
      if (data && ACTIVE_COARSE.has(data.status)) return 3000
      return false
    },
  })

  const subprojects = useQuery({
    queryKey: ['subprojects', id],
    queryFn: () => getSubprojects(id),
  })

  const addMutation = useMutation({
    mutationFn: (url: string) => addResource(id, url),
    onSuccess: async (resource) => {
      await queryClient.invalidateQueries({ queryKey: ['resources', id] })
      setSelectedResourceId(resource.id)
      setNewUrl('')
    },
    onError: () => setUrlError('Failed to add resource.'),
  })

  const acceptMut = useMutation({
    mutationFn: ({ resourceId, idx, edits }: { resourceId: string; idx: number; edits: Record<string, string> }) =>
      acceptProposal(resourceId, idx, edits),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['resource', selectedResourceId] })
      await queryClient.invalidateQueries({ queryKey: ['subprojects', id] })
      await queryClient.invalidateQueries({ queryKey: ['projects'] })
      await queryClient.invalidateQueries({ queryKey: ['project', id] })
    },
  })

  const rejectMut = useMutation({
    mutationFn: ({ resourceId, idx }: { resourceId: string; idx: number }) =>
      rejectProposal(resourceId, idx),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['resource', selectedResourceId] })
    },
  })

  const handleAddResource = () => {
    const trimmed = newUrl.trim()
    if (!trimmed) { setUrlError('URL is required'); return }
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      setUrlError('URL must start with http:// or https://')
      return
    }
    setUrlError('')
    addMutation.mutate(trimmed)
  }

  if (isPending) return <div className="p-8 text-sm text-zinc-400">Loading project…</div>
  if (error || !project) return <div className="p-8"><StatusBadge status="error" label="Project not found" /></div>

  const sel = selectedResource.data
  const proposals = sel?.extraction?.discovered_projects

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Project header */}
      <div className="flex items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">{project.name}</h1>
          {project.description && <p className="mt-1 text-sm text-zinc-400">{project.description}</p>}
        </div>
        <div className="text-xs text-zinc-500">{project.subproject_count} subprojects</div>
      </div>

      {/* Three-panel workspace */}
      <div className="grid min-h-0 flex-1 grid-cols-[280px_1fr_300px] gap-4">

        {/* Left: Resources + Subprojects */}
        <section className="flex flex-col gap-3 overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          {/* Add resource */}
          <h2 className="text-xs uppercase tracking-wide text-zinc-500">Resources</h2>
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
          <div className="space-y-2">
            {resources.data?.map((r) => (
              <ResourceCard
                key={r.id}
                resource={r}
                selected={r.id === selectedResourceId}
                onClick={() => setSelectedResourceId(r.id)}
              />
            ))}
          </div>

          {/* Subprojects */}
          {subprojects.data && subprojects.data.length > 0 && (
            <>
              <h2 className="mt-4 text-xs uppercase tracking-wide text-zinc-500">
                Subprojects ({subprojects.data.length})
              </h2>
              <div className="space-y-1">
                {subprojects.data.map((sp) => (
                  <div
                    key={sp.id}
                    className="flex items-center gap-2 rounded-md border border-emerald-500/20 bg-emerald-500/5 px-3 py-2"
                  >
                    <Folder size={14} className="text-emerald-400" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm text-zinc-200">{sp.name}</div>
                      <div className="text-xs text-zinc-500">{sp.type} · {sp.complexity}</div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {!resources.data?.length && !subprojects.data?.length && (
            <p className="text-sm text-zinc-400">No resources yet. Add a URL to get started.</p>
          )}
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
                  <p className="mt-2 text-sm leading-relaxed text-zinc-300">{sel.extraction.summary}</p>
                  {sel.extraction.model_used === 'fallback' && (
                    <p className="mt-1 text-xs text-amber-400">⚠ Placeholder result — no LLM provider was available</p>
                  )}
                </div>
              )}

              {sel.extraction?.key_concepts && sel.extraction.key_concepts.length > 0 && (
                <div>
                  <h3 className="text-xs uppercase tracking-wide text-zinc-500">Key Concepts</h3>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {sel.extraction.key_concepts.map((c, i) => (
                      <span key={i} className="rounded-full border border-zinc-700 bg-zinc-800 px-2 py-0.5 text-xs text-zinc-300">{c}</span>
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

        {/* Right: Proposals */}
        <section className="overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-xs uppercase tracking-wide text-zinc-500">Discovered Projects</h2>
          {proposals && proposals.length > 0 ? (
            <div className="mt-3 space-y-3">
              {proposals.map((p, i) => (
                <ProposalCard
                  key={i}
                  proposal={p}
                  index={i}
                  disabled={acceptMut.isPending || rejectMut.isPending}
                  onAccept={(idx, edits) =>
                    acceptMut.mutate({ resourceId: sel!.id, idx, edits })
                  }
                  onReject={(idx) =>
                    rejectMut.mutate({ resourceId: sel!.id, idx })
                  }
                />
              ))}
            </div>
          ) : sel && sel.pipeline_status === 'discovered' ? (
            <p className="mt-3 text-sm text-zinc-400">No projects discovered.</p>
          ) : sel ? (
            <p className="mt-3 text-sm text-zinc-400">Waiting for analysis…</p>
          ) : (
            <p className="mt-3 text-sm text-zinc-400">Select a resource to see proposals.</p>
          )}
        </section>
      </div>
    </div>
  )
}
