import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { ArrowLeft, ExternalLink, FolderX, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'

import { useAppStore } from '@/stores/app'

import {
  generateStarterTasks,
  getFileContent,
  getSubprojectDetail,
  getSubprojectFiles,
  getTasks,
} from '@/api/client'
import { StatusBadge } from '@/components/common/StatusBadge'
import { FileTree } from '@/components/workspace/FileTree'
import { NoteEditor } from '@/components/workspace/NoteEditor'
import { TaskList } from '@/components/workspace/TaskList'

interface SubprojectRouteProps {
  id: string
}

type Tab = 'files' | 'tasks' | 'notes' | 'next-steps'

export function SubprojectRoute({ id }: SubprojectRouteProps) {
  const queryClient = useQueryClient()
  const setAgentContext = useAppStore((s) => s.setAgentContext)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Tab>('files')

  useEffect(() => {
    setAgentContext({ subprojectId: id })
    return () => setAgentContext({})
  }, [id, setAgentContext])

  const { data: sub, isPending, error } = useQuery({
    queryKey: ['subproject', id],
    queryFn: () => getSubprojectDetail(id),
  })

  const files = useQuery({
    queryKey: ['subproject-files', id],
    queryFn: () => getSubprojectFiles(id),
    enabled: !!sub,
  })

  const fileContent = useQuery({
    queryKey: ['file-content', id, selectedFile],
    queryFn: () => (selectedFile ? getFileContent(id, selectedFile) : Promise.reject()),
    enabled: !!selectedFile,
  })

  const tasks = useQuery({
    queryKey: ['tasks', id],
    queryFn: () => getTasks(id),
    enabled: activeTab === 'next-steps',
  })

  const generateMut = useMutation({
    mutationFn: () => generateStarterTasks(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks', id] }),
  })

  if (isPending) return <div className="p-8 text-sm text-zinc-400">Loading subproject…</div>
  if (error || !sub) return <div className="p-8"><StatusBadge status="error" label="Subproject not found" /></div>

  const readmePath = files.data?.entries.find((e) => e.name.toLowerCase() === 'readme.md')?.path
  const activeFile = selectedFile ?? readmePath ?? null

  const tabs: Array<{ id: Tab; label: string }> = [
    { id: 'files', label: 'Files' },
    { id: 'tasks', label: 'Tasks' },
    { id: 'notes', label: 'Notes' },
    { id: 'next-steps', label: 'Next Steps' },
  ]

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <Link
          to="/project/$id"
          params={{ id: sub.project_id }}
          className="rounded-md p-1 text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-zinc-200"
        >
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1">
          <h1 className="text-lg font-semibold text-zinc-100">{sub.name}</h1>
          {sub.description && <p className="mt-0.5 text-sm text-zinc-400">{sub.description}</p>}
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-xs text-zinc-400">{sub.type}</span>
          <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-xs text-zinc-400">{sub.complexity}</span>
        </div>
      </div>

      {/* Two-panel layout */}
      <div className="grid min-h-0 flex-1 grid-cols-[240px_1fr] gap-4">
        {/* Left: File tree */}
        <section className="flex flex-col gap-3 overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-3">
          <h2 className="text-xs uppercase tracking-wide text-zinc-500">Files</h2>
          {!sub.workspace_exists ? (
            <div className="flex flex-col items-center gap-2 py-4 text-zinc-500">
              <FolderX size={24} />
              <p className="text-xs">Workspace missing</p>
            </div>
          ) : files.data ? (
            <FileTree entries={files.data.entries} selectedPath={activeFile} onSelect={(p) => { setSelectedFile(p); setActiveTab('files') }} />
          ) : (
            <p className="text-xs text-zinc-500">Loading files…</p>
          )}
        </section>

        {/* Right: Tabbed content + metadata */}
        <section className="flex flex-col gap-4 overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          {/* Tabs */}
          <div className="flex gap-1 border-b border-zinc-800 pb-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-zinc-800 text-zinc-100'
                    : 'text-zinc-500 hover:bg-zinc-800/50 hover:text-zinc-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="min-h-0 flex-1 overflow-auto">
            {activeTab === 'files' && (
              activeFile && fileContent.data ? (
                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="text-xs uppercase tracking-wide text-zinc-500">{activeFile}</h3>
                    <span className="text-xs text-zinc-600">{formatSize(fileContent.data.size)}</span>
                  </div>
                  <pre className="max-h-[400px] overflow-auto rounded-lg border border-zinc-800 bg-zinc-950 p-3 text-xs leading-relaxed text-zinc-300">
                    {fileContent.data.content}
                  </pre>
                </div>
              ) : activeFile && fileContent.isPending ? (
                <p className="text-sm text-zinc-500">Loading file…</p>
              ) : (
                <p className="text-sm text-zinc-500">Select a file to view its content.</p>
              )
            )}

            {activeTab === 'tasks' && <TaskList subprojectId={id} />}

            {activeTab === 'notes' && <NoteEditor subprojectId={id} />}

            {activeTab === 'next-steps' && (
              <div className="space-y-4">
                {/* Generate starter tasks button */}
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => generateMut.mutate()}
                    disabled={generateMut.isPending}
                    className="inline-flex items-center gap-1.5 rounded-md bg-blue-500 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-400 disabled:opacity-50"
                  >
                    <Sparkles size={13} />
                    {generateMut.isPending ? 'Generating…' : 'Generate Starter Tasks'}
                  </button>
                  <span className="text-xs text-zinc-500">Creates tasks from setup steps, deps, and sources</span>
                </div>

                {/* Dependencies */}
                {sub.dependencies && sub.dependencies.length > 0 && (
                  <div>
                    <h3 className="text-xs uppercase tracking-wide text-zinc-500">Dependencies</h3>
                    <div className="mt-2 flex flex-wrap gap-1">
                      {sub.dependencies.map((d, i) => (
                        <span key={i} className="rounded-full border border-zinc-700 bg-zinc-800 px-2 py-0.5 text-xs text-zinc-300">{d}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Setup Steps */}
                {sub.setup_steps && sub.setup_steps.length > 0 && (
                  <div>
                    <h3 className="text-xs uppercase tracking-wide text-zinc-500">Setup Steps</h3>
                    <ol className="mt-2 list-inside list-decimal space-y-1 text-sm text-zinc-400">
                      {sub.setup_steps.map((s, i) => <li key={i}>{s}</li>)}
                    </ol>
                  </div>
                )}

                {/* Tasks (if generated) */}
                {tasks.data && tasks.data.length > 0 && (
                  <div>
                    <h3 className="text-xs uppercase tracking-wide text-zinc-500">Tasks ({tasks.data.length})</h3>
                    <div className="mt-2 space-y-1">
                      {tasks.data.map((t) => (
                        <div key={t.id} className="flex items-center gap-2 text-sm">
                          <span className={t.status === 'done' ? 'text-emerald-400' : 'text-zinc-500'}>
                            {t.status === 'done' ? '✓' : '○'}
                          </span>
                          <span className={t.status === 'done' ? 'text-zinc-500 line-through' : 'text-zinc-300'}>
                            {t.title}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Links / Repos from provenance */}
                {sub.provenance && sub.provenance.length > 0 && (
                  <div>
                    <h3 className="text-xs uppercase tracking-wide text-zinc-500">Source Resources</h3>
                    {sub.provenance.map((prov) => (
                      <div key={prov.id} className="mt-2 rounded-lg border border-zinc-800 bg-zinc-950 p-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-zinc-200">{prov.resource_title || 'Resource'}</span>
                          {prov.resource_url && (
                            <a href={prov.resource_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">
                              <ExternalLink size={12} />
                            </a>
                          )}
                        </div>
                        {prov.context && <p className="mt-1 text-xs italic text-zinc-500">"{prov.context}"</p>}
                        <span className={`text-xs ${prov.confidence >= 0.7 ? 'text-emerald-400' : prov.confidence >= 0.3 ? 'text-amber-400' : 'text-zinc-500'}`}>
                          Confidence: {Math.round(prov.confidence * 100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Metadata (always visible below tabs) */}
          <div className="border-t border-zinc-800 pt-4">
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <span className="text-zinc-500">Status</span>
              <span className="text-zinc-300">{sub.status}</span>
              <span className="text-zinc-500">Created</span>
              <span className="text-zinc-300">{sub.created_at ? new Date(sub.created_at).toLocaleDateString() : '—'}</span>
              <span className="text-zinc-500">Workspace</span>
              <span className="truncate text-zinc-300" title={sub.workspace_path}>{sub.workspace_path}</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}K`
  return `${(bytes / (1024 * 1024)).toFixed(1)}M`
}
