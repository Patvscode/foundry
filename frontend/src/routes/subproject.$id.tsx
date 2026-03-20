import { useQuery } from '@tanstack/react-query'
import { Link } from '@tanstack/react-router'
import { ArrowLeft, ExternalLink, FolderX } from 'lucide-react'
import { useState } from 'react'

import { getFileContent, getSubprojectDetail, getSubprojectFiles } from '@/api/client'
import { StatusBadge } from '@/components/common/StatusBadge'
import { FileTree } from '@/components/workspace/FileTree'

interface SubprojectRouteProps {
  id: string
}

export function SubprojectRoute({ id }: SubprojectRouteProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)

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

  if (isPending) return <div className="p-8 text-sm text-zinc-400">Loading subproject…</div>
  if (error || !sub) return <div className="p-8"><StatusBadge status="error" label="Subproject not found" /></div>

  // Auto-select README if nothing selected
  const readmePath = files.data?.entries.find((e) => e.name.toLowerCase() === 'readme.md')?.path
  const activeFile = selectedFile ?? readmePath ?? null

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
            <FileTree
              entries={files.data.entries}
              selectedPath={activeFile}
              onSelect={setSelectedFile}
            />
          ) : (
            <p className="text-xs text-zinc-500">Loading files…</p>
          )}
        </section>

        {/* Right: Detail */}
        <section className="flex flex-col gap-4 overflow-auto rounded-lg border border-zinc-800 bg-zinc-900 p-4">
          {/* File content viewer */}
          {activeFile && fileContent.data ? (
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
          ) : null}

          {/* Metadata */}
          <div>
            <h3 className="text-xs uppercase tracking-wide text-zinc-500">Details</h3>
            <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <div className="text-zinc-500">Type</div>
              <div className="text-zinc-300">{sub.type}</div>
              <div className="text-zinc-500">Complexity</div>
              <div className="text-zinc-300">{sub.complexity}</div>
              <div className="text-zinc-500">Status</div>
              <div className="text-zinc-300">{sub.status}</div>
              <div className="text-zinc-500">Created</div>
              <div className="text-zinc-300">{sub.created_at ? new Date(sub.created_at).toLocaleDateString() : '—'}</div>
              <div className="text-zinc-500">Workspace</div>
              <div className="truncate text-zinc-300" title={sub.workspace_path}>{sub.workspace_path}</div>
            </div>
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

          {/* Provenance */}
          {sub.provenance && sub.provenance.length > 0 && (
            <div>
              <h3 className="text-xs uppercase tracking-wide text-zinc-500">Source</h3>
              {sub.provenance.map((prov) => (
                <div key={prov.id} className="mt-2 rounded-lg border border-zinc-800 bg-zinc-950 p-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-zinc-200">{prov.resource_title || 'Unknown resource'}</span>
                    {prov.resource_url && (
                      <a
                        href={prov.resource_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300"
                      >
                        <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                  {prov.context && (
                    <p className="mt-1 text-xs italic text-zinc-500">"{prov.context}"</p>
                  )}
                  <div className="mt-1">
                    <span className={`text-xs ${
                      prov.confidence >= 0.7 ? 'text-emerald-400'
                      : prov.confidence >= 0.3 ? 'text-amber-400'
                      : 'text-zinc-500'
                    }`}>
                      Confidence: {Math.round(prov.confidence * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
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
