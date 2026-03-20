import { useNavigate } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'
import { searchAll, type SearchResult } from '@/api/client'

const QUICK_ACTIONS = [
  { id: 'new-project', label: 'New Project', icon: '📁', path: '/' },
  { id: 'settings', label: 'Settings', icon: '⚙️', path: '/settings' },
  { id: 'dashboard', label: 'Dashboard', icon: '🏠', path: '/' },
]

const TYPE_ICONS: Record<string, string> = {
  project: '📁',
  resource: '🔗',
  subproject: '📦',
  task: '✅',
  note: '📝',
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [selected, setSelected] = useState(0)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (open) {
      setQuery('')
      setResults([])
      setSelected(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      return
    }
    const timer = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await searchAll(query)
        setResults(data.results)
        setSelected(0)
      } catch {
        setResults([])
      }
      setLoading(false)
    }, 200)
    return () => clearTimeout(timer)
  }, [query])

  const allItems = query.trim()
    ? results.map((r) => ({
        id: r.entity_id,
        label: r.title,
        icon: TYPE_ICONS[r.entity_type] || '📄',
        type: r.entity_type,
        snippet: r.snippet,
      }))
    : QUICK_ACTIONS.map((a) => ({ ...a, type: 'action', snippet: '' }))

  const handleSelect = (item: (typeof allItems)[0]) => {
    onClose()
    if (item.type === 'action') {
      const action = QUICK_ACTIONS.find((a) => a.id === item.id)
      if (action) navigate({ to: action.path })
    } else if (item.type === 'project') {
      navigate({ to: '/project/$id', params: { id: item.id } })
    } else if (item.type === 'subproject') {
      navigate({ to: '/subproject/$id', params: { id: item.id } })
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelected((s) => Math.min(s + 1, allItems.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelected((s) => Math.max(s - 1, 0))
    } else if (e.key === 'Enter' && allItems[selected]) {
      handleSelect(allItems[selected])
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60" />
      <div
        className="relative w-full max-w-lg rounded-xl border border-zinc-700 bg-zinc-900 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center border-b border-zinc-800 px-4">
          <span className="mr-2 text-zinc-500">🔍</span>
          <input
            ref={inputRef}
            type="text"
            placeholder="Search projects, resources, tasks…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="h-12 flex-1 bg-transparent text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
          />
          {loading && <span className="text-xs text-zinc-500">…</span>}
          <kbd className="ml-2 rounded border border-zinc-700 bg-zinc-800 px-1.5 py-0.5 text-xs text-zinc-400">
            esc
          </kbd>
        </div>

        <div className="max-h-72 overflow-y-auto py-2">
          {allItems.length === 0 && query.trim() && (
            <div className="px-4 py-3 text-sm text-zinc-500">No results found</div>
          )}
          {allItems.map((item, i) => (
            <button
              key={`${item.type}-${item.id}`}
              type="button"
              onClick={() => handleSelect(item)}
              className={`flex w-full items-center gap-3 px-4 py-2 text-left text-sm transition-colors ${
                i === selected ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-300 hover:bg-zinc-800/50'
              }`}
            >
              <span>{item.icon}</span>
              <div className="flex-1 overflow-hidden">
                <div className="truncate font-medium">{item.label}</div>
                {item.snippet && (
                  <div
                    className="truncate text-xs text-zinc-500"
                    dangerouslySetInnerHTML={{ __html: item.snippet }}
                  />
                )}
              </div>
              <span className="text-xs text-zinc-600">{item.type}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
