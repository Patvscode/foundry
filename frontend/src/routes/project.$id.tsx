import { useQuery } from '@tanstack/react-query'

import { getProject } from '@/api/client'
import { StatusBadge } from '@/components/common/StatusBadge'

interface ProjectWorkspaceRouteProps {
  id: string
}

export function ProjectWorkspaceRoute({ id }: ProjectWorkspaceRouteProps) {
  const { data: project, isPending, error } = useQuery({
    queryKey: ['project', id],
    queryFn: () => getProject(id),
  })

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

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Project header */}
      <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h1 className="text-lg font-semibold text-zinc-100">{project.name}</h1>
        {project.description && <p className="mt-1 text-sm text-zinc-400">{project.description}</p>}
        <div className="mt-2 flex items-center gap-3 text-xs text-zinc-500">
          <StatusBadge status="healthy" label={project.status} />
          <span>{project.subproject_count} subprojects</span>
        </div>
      </div>

      {/* Three-panel workspace */}
      <div className="grid min-h-0 flex-1 grid-cols-[260px_1fr_280px] gap-4">
        <section className="overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-xs uppercase tracking-wide text-zinc-500">Resources</h2>
          <p className="mt-3 text-sm text-zinc-400">No resources yet. Add a URL to get started.</p>
        </section>

        <section className="overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-xs uppercase tracking-wide text-zinc-500">Workspace</h2>
          <p className="mt-3 text-sm text-zinc-400">Add a resource to begin analysis.</p>
        </section>

        <section className="overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          <h2 className="text-xs uppercase tracking-wide text-zinc-500">Context</h2>
          <p className="mt-3 text-sm text-zinc-400">Select an item to see details.</p>
        </section>
      </div>
    </div>
  )
}
