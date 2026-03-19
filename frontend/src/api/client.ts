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
  id?: string
  name?: string | null
  description?: string | null
  status?: string
  workspace_path?: string | null
  created_at?: string | null
  updated_at?: string | null
  [key: string]: unknown
}

export type ConfigResponse = Record<string, unknown>

export interface VersionResponse {
  name: string
  version: string
}

const API_BASE_URL = ''

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`)
  }

  return (await response.json()) as T
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/api/system/health')
}

export function getProjects(): Promise<Project[]> {
  return request<Project[]>('/api/projects')
}

export function getConfig(): Promise<ConfigResponse> {
  return request<ConfigResponse>('/api/system/config')
}

export function getVersion(): Promise<VersionResponse> {
  return request<VersionResponse>('/api/system/version')
}
