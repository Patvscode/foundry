import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { Folder, LayoutDashboard, Plus, Settings } from 'lucide-react'

import { getProjects } from '@/api/client'
import { useAppStore } from '@/stores/app'

const navLinkClass =
  'flex items-center gap-2 rounded-md px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50'

const navLinkActiveClass = `${navLinkClass} bg-zinc-800 text-zinc-100`

export function Sidebar() {
  const sidebarOpen = useAppStore((s) => s.sidebarOpen)
  const toggleSidebar = useAppStore((s) => s.toggleSidebar)

  const projects = useQuery({ queryKey: ['projects'], queryFn: getProjects })

  return (
    <aside
      className={`flex h-full flex-col border-r border-zinc-800 bg-zinc-900 p-4 transition-all ${
        sidebarOpen ? 'w-72' : 'w-16'
      }`}
    >
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        {sidebarOpen ? (
          <div>
            <div className="text-sm text-zinc-400">Workbench</div>
            <h1 className="text-lg font-semibold text-zinc-100">Foundry</h1>
          </div>
        ) : (
          <span className="mx-auto text-lg font-semibold text-zinc-100">F</span>
        )}
        <button
          type="button"
          onClick={toggleSidebar}
          className="rounded-md border border-zinc-800 px-2 py-1 text-xs text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
          aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          {sidebarOpen ? '◀' : '▶'}
        </button>
      </div>

      {sidebarOpen ? (
        <>
          {/* Navigation */}
          <nav className="space-y-1">
            <Link to="/" className={navLinkClass} activeProps={{ className: navLinkActiveClass }}>
              <LayoutDashboard size={16} />
              Dashboard
            </Link>
            <Link to="/settings" className={navLinkClass} activeProps={{ className: navLinkActiveClass }}>
              <Settings size={16} />
              Settings
            </Link>
          </nav>

          {/* New Project */}
          <Link
            to="/"
            className="mt-4 inline-flex items-center justify-center gap-2 rounded-md bg-blue-500 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
          >
            <Plus size={16} />
            New Project
          </Link>

          {/* Project List */}
          <div className="mt-6 flex-1 overflow-auto">
            <h2 className="text-xs uppercase tracking-wide text-zinc-500">
              Projects{projects.data?.length ? ` (${projects.data.length})` : ''}
            </h2>
            <div className="mt-3 space-y-1">
              {projects.data?.length ? (
                projects.data.map((p) => (
                  <Link
                    key={p.id}
                    to="/project/$id"
                    params={{ id: p.id }}
                    className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-zinc-100"
                    activeProps={{ className: 'flex items-center gap-2 rounded-md bg-zinc-800 px-3 py-2 text-sm text-zinc-100' }}
                  >
                    <Folder size={14} />
                    <span className="truncate">{p.name}</span>
                  </Link>
                ))
              ) : (
                <div className="rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-sm text-zinc-400">
                  No projects yet
                </div>
              )}
            </div>
          </div>
        </>
      ) : (
        <div className="mt-2 flex flex-1 flex-col items-center gap-2">
          <Link
            to="/"
            className="rounded-md p-2 text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
            activeProps={{ className: 'rounded-md bg-zinc-800 p-2 text-zinc-100' }}
            aria-label="Dashboard"
          >
            <LayoutDashboard size={16} />
          </Link>
          <Link
            to="/settings"
            className="rounded-md p-2 text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
            activeProps={{ className: 'rounded-md bg-zinc-800 p-2 text-zinc-100' }}
            aria-label="Settings"
          >
            <Settings size={16} />
          </Link>
        </div>
      )}
    </aside>
  )
}
