export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'error'
  version: string
  uptime_seconds: number
  db: 'ok' | 'error'
  workspace: 'ok' | 'error'
  disk_free_gb: number
  agent_provider: string
  active_projects: number
  active_ingestions: number
  pending_reconcile_issues: number
}

export interface Project {
  id: string
  name: string
  description: string
  status: string
  workspace_path: string
  subproject_count: number
  created_at: string
  updated_at: string
}

export type ConfigResponse = Record<string, unknown>

export interface VersionResponse {
  name: string
  version: string
}

const API_BASE = ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    ...init,
  })

  if (!response.ok) {
    throw new Error(`API ${response.status}: ${response.statusText}`)
  }

  return (await response.json()) as T
}

// ── System ─────────────────────────────────────────────────────

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/system/health')
}

export function getConfig(): Promise<ConfigResponse> {
  return request<ConfigResponse>('/api/system/config')
}

export function getVersion(): Promise<VersionResponse> {
  return request<VersionResponse>('/api/system/version')
}

// ── Projects ───────────────────────────────────────────────────

export function getProjects(): Promise<Project[]> {
  return request<Project[]>('/api/projects')
}

export function getProject(id: string): Promise<Project> {
  return request<Project>(`/api/projects/${id}`)
}

export function createProject(name: string, description = ''): Promise<Project> {
  return request<Project>('/api/projects', {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  })
}
