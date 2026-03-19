interface ProjectWorkspaceRouteProps {
  id: string
}

export function ProjectWorkspaceRoute({ id }: ProjectWorkspaceRouteProps) {
  return (
    <div className="grid h-full min-h-[calc(100vh-7.5rem)] grid-cols-[260px_1fr_280px] gap-4">
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h1 className="text-base font-semibold text-zinc-100">Project: {id}</h1>
        <p className="mt-2 text-sm text-zinc-400">Project Browser</p>
      </section>

      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="text-sm font-medium text-zinc-300">Main Panel</h2>
      </section>

      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="text-sm font-medium text-zinc-300">Context Panel</h2>
      </section>
    </div>
  )
}
