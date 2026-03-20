import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { useState } from 'react'

import { createProject, getHealth, getProjects } from '@/api/client'
import { StatusBadge } from '@/components/common/StatusBadge'
import { ProviderStatus } from '@/components/common/ProviderStatus'

const MAX_NAME_LENGTH = 200

export function DashboardRoute() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [newName, setNewName] = useState('')
  const [nameError, setNameError] = useState('')

  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, retry: 1 })
  const projects = useQuery({ queryKey: ['projects'], queryFn: getProjects })

  const create = useMutation({
    mutationFn: (name: string) => createProject(name),
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: ['projects'] })
      await navigate({ to: '/project/$id', params: { id: project.id } })
    },
    onError: () => {
      setNameError('Failed to create project. Try again.')
    },
  })

  const validateAndCreate = () => {
    const trimmed = newName.trim()
    if (!trimmed) {
      setNameError('Project name is required')
      return
    }
    if (trimmed.length > MAX_NAME_LENGTH) {
      setNameError(`Name must be ${MAX_NAME_LENGTH} characters or less`)
      return
    }
    setNameError('')
    setNewName('')
    create.mutate(trimmed)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      validateAndCreate()
    }
  }

  const hasProjects = (projects.data?.length ?? 0) > 0

  return (
    <div className="mx-auto flex h-full w-full max-w-4xl flex-col gap-4">
      {/* System status */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <h2 className="text-sm font-medium text-zinc-300">System Status</h2>
        <div className="mt-3">
          {health.isPending ? (
            <span className="text-sm text-zinc-400">Checking backend health…</span>
          ) : health.error ? (
            <div className="space-y-2">
              <StatusBadge status="error" label="Backend unreachable" />
              <p className="text-sm text-zinc-400">Could not connect to /api/system/health.</p>
            </div>
          ) : health.data ? (
            <div className="space-y-2">
              <StatusBadge
                status={health.data.status === 'healthy' ? 'healthy' : 'degraded'}
                label={health.data.status}
              />
              <p className="text-sm text-zinc-400">
                Version {health.data.version} · DB {health.data.db} · Workspace {health.data.workspace}
              </p>
            </div>
          ) : null}
        </div>
      </section>

      {/* Provider status */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <ProviderStatus compact />
      </section>

      {/* Create project */}
      <section className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="New project name…"
            value={newName}
            onChange={(e) => {
              setNewName(e.target.value)
              if (nameError) setNameError('')
            }}
            onKeyDown={handleKeyDown}
            maxLength={MAX_NAME_LENGTH + 1}
            className={`h-9 flex-1 rounded-md border bg-zinc-950 px-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50 ${
              nameError ? 'border-red-500' : 'border-zinc-800'
            }`}
          />
          <button
            type="button"
            onClick={validateAndCreate}
            disabled={create.isPending}
            className="rounded-md bg-blue-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-400 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
          >
            {create.isPending ? 'Creating…' : 'New Project'}
          </button>
        </div>
        {nameError && <p className="mt-2 text-xs text-red-400">{nameError}</p>}
      </section>

      {/* Project list or empty state */}
      {hasProjects ? (
        <section className="space-y-2">
          {projects.data?.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => navigate({ to: '/project/$id', params: { id: p.id } })}
              className="flex w-full items-center justify-between rounded-lg border border-zinc-800 bg-zinc-900 p-4 text-left transition-colors hover:border-zinc-700 hover:bg-zinc-800"
            >
              <div>
                <div className="text-sm font-medium text-zinc-100">{p.name}</div>
                {p.description && <div className="mt-1 text-xs text-zinc-400">{p.description}</div>}
              </div>
              <div className="text-xs text-zinc-500">{p.subproject_count} subprojects</div>
            </button>
          ))}
        </section>
      ) : !projects.isPending ? (
        <section className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-zinc-800 bg-zinc-900 p-8">
          <div className="max-w-lg space-y-3 text-center">
            <h1 className="text-2xl font-semibold text-zinc-100">🔥 No projects yet</h1>
            <p className="text-zinc-400">Type a project name above and click New Project to get started.</p>
          </div>
        </section>
      ) : null}
    </div>
  )
}
