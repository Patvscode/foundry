import { Link } from '@tanstack/react-router'
import { LayoutDashboard, Plus, Settings } from 'lucide-react'

import { useAppStore } from '@/stores/app'

const navLinkClass =
  'flex items-center gap-2 rounded-md px-3 py-2 text-sm text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50'

export function Sidebar() {
  const sidebarOpen = useAppStore((state) => state.sidebarOpen)
  const toggleSidebar = useAppStore((state) => state.toggleSidebar)

  return (
    <aside
      className={`flex h-full flex-col border-r border-zinc-800 bg-zinc-900 p-4 transition-all ${
        sidebarOpen ? 'w-72' : 'w-16'
      }`}
    >
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
          {sidebarOpen ? '<' : '>'}
        </button>
      </div>

      {sidebarOpen ? (
        <>
          <nav className="space-y-1">
            <Link to="/" className={navLinkClass} activeProps={{ className: `${navLinkClass} bg-zinc-800 text-zinc-100` }}>
              <LayoutDashboard size={16} />
              Dashboard
            </Link>
            <Link
              to="/settings"
              className={navLinkClass}
              activeProps={{ className: `${navLinkClass} bg-zinc-800 text-zinc-100` }}
            >
              <Settings size={16} />
              Settings
            </Link>
          </nav>

          <button
            type="button"
            className="mt-4 inline-flex items-center justify-center gap-2 rounded-md bg-blue-500 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
          >
            <Plus size={16} />
            New Project
          </button>

          <div className="mt-6 flex-1">
            <h2 className="text-xs uppercase tracking-wide text-zinc-500">Projects</h2>
            <div className="mt-3 rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-sm text-zinc-400">No projects yet</div>
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
