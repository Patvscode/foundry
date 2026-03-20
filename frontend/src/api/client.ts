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

// ── Resources ──────────────────────────────────────────────────

export interface Resource {
  id: string
  project_id: string
  type: string
  url: string
  title: string | null
  status: 'pending' | 'processing' | 'completed' | 'failed'
  pipeline_status: string
  pipeline_error: string | null
  content_hash: string | null
  created_at: string
  updated_at: string
  extraction?: ExtractionResult | null
}

export interface ExtractionResult {
  id: string
  resource_id: string
  summary: string | null
  key_concepts: string[] | null
  entities: Record<string, unknown[]> | null
  content_sections: Array<{ title: string; summary: string }> | null
  discovered_projects: SubprojectProposal[] | null
  open_questions: string[] | null
  model_used: string | null
}

export interface SubprojectProposal {
  proposal_id: string
  suggested_name: string
  description: string
  type: string
  repos: string[]
  dependencies: string[]
  setup_steps: string[]
  complexity: string
  confidence: number
  source_context: string
  is_synthetic: boolean
  decision: string | null
  decision_at: string | null
  subproject_id: string | null
  edited_name: string | null
  edited_description: string | null
  edited_type: string | null
}

export function getResources(projectId: string): Promise<Resource[]> {
  return request<Resource[]>(`/api/projects/${projectId}/resources`)
}

export function getResource(resourceId: string): Promise<Resource> {
  return request<Resource>(`/api/resources/${resourceId}`)
}

export function addResource(projectId: string, url: string): Promise<Resource> {
  return request<Resource>(`/api/projects/${projectId}/resources`, {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

// ── Subprojects ────────────────────────────────────────────────

export interface Subproject {
  id: string
  project_id: string
  name: string
  description: string
  type: string
  status: string
  workspace_path: string
  dependencies: string[]
  setup_steps: string[]
  complexity: string
  sort_order: number
  created_at: string
  updated_at: string
}

export function acceptProposal(resourceId: string, proposalId: string): Promise<Subproject> {
  return request<Subproject>(`/api/resources/${resourceId}/proposals/${proposalId}/accept`, {
    method: 'POST',
  })
}

export function rejectProposal(resourceId: string, proposalId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/api/resources/${resourceId}/proposals/${proposalId}/reject`, {
    method: 'POST',
  })
}

export function editProposal(
  resourceId: string,
  proposalId: string,
  edits: { edited_name?: string; edited_description?: string; edited_type?: string },
): Promise<SubprojectProposal> {
  return request<SubprojectProposal>(`/api/resources/${resourceId}/proposals/${proposalId}`, {
    method: 'PUT',
    body: JSON.stringify(edits),
  })
}

export function getSubprojects(projectId: string): Promise<Subproject[]> {
  return request<Subproject[]>(`/api/projects/${projectId}/subprojects`)
}

// ── Subproject Detail ──────────────────────────────────────────

export interface ProvenanceLink {
  id: string
  resource_id: string
  resource_url: string | null
  resource_title: string | null
  target_type: string
  target_id: string
  context: string | null
  confidence: number
}

export interface SubprojectDetail extends Subproject {
  provenance: ProvenanceLink[]
  workspace_exists: boolean
}

export interface FileEntry {
  name: string
  path: string
  is_dir: boolean
  size?: number
}

export interface FileTreeResponse {
  workspace_exists: boolean
  entries: FileEntry[]
}

export interface FileContentResponse {
  path: string
  size: number
  content: string
}

// ── Tasks ──────────────────────────────────────────────────────

export interface Task {
  id: string
  subproject_id: string
  title: string
  description: string
  status: 'todo' | 'done'
  source: 'user' | 'extracted'
  sort_order: number
  created_at: string
  updated_at: string
}

export function getTasks(subprojectId: string): Promise<Task[]> {
  return request<Task[]>(`/api/subprojects/${subprojectId}/tasks`)
}

export function createTask(subprojectId: string, title: string, description = ''): Promise<Task> {
  return request<Task>(`/api/subprojects/${subprojectId}/tasks`, {
    method: 'POST',
    body: JSON.stringify({ title, description }),
  })
}

export function updateTask(
  subprojectId: string,
  taskId: string,
  fields: { title?: string; description?: string; status?: string },
): Promise<Task> {
  return request<Task>(`/api/subprojects/${subprojectId}/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(fields),
  })
}

export function generateStarterTasks(subprojectId: string): Promise<Task[]> {
  return request<Task[]>(`/api/subprojects/${subprojectId}/tasks/generate`, {
    method: 'POST',
  })
}

// ── Notes ──────────────────────────────────────────────────────

export interface Note {
  id: string
  subproject_id: string
  title: string
  content: string
  source: string
  created_at: string
  updated_at: string
}

export function getNotes(subprojectId: string): Promise<Note[]> {
  return request<Note[]>(`/api/subprojects/${subprojectId}/notes`)
}

export function createNote(subprojectId: string, title: string, content = ''): Promise<Note> {
  return request<Note>(`/api/subprojects/${subprojectId}/notes`, {
    method: 'POST',
    body: JSON.stringify({ title, content }),
  })
}

export function updateNote(
  subprojectId: string,
  noteId: string,
  fields: { title?: string; content?: string },
): Promise<Note> {
  return request<Note>(`/api/subprojects/${subprojectId}/notes/${noteId}`, {
    method: 'PATCH',
    body: JSON.stringify(fields),
  })
}

export function deleteNote(subprojectId: string, noteId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/api/subprojects/${subprojectId}/notes/${noteId}`, {
    method: 'DELETE',
  })
}

// ── Agent Chat ─────────────────────────────────────────────────

export interface ChatMessage {
  id: string
  session_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export interface ChatResponse {
  session_id: string
  message: string
  is_synthetic: boolean
  provider: string
  suggestions: Array<{ type: 'task' | 'note'; title: string }>
}

export interface AgentSession {
  id: string
  project_id: string | null
  subproject_id: string | null
  provider: string
  status: string
  messages: ChatMessage[]
}

export function sendAgentMessage(params: {
  message: string
  session_id?: string
  project_id?: string
  resource_id?: string
  subproject_id?: string
}): Promise<ChatResponse> {
  return request<ChatResponse>('/api/agent/chat', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

export function getAgentSession(sessionId: string): Promise<AgentSession> {
  return request<AgentSession>(`/api/agent/sessions/${sessionId}`)
}

export function executeAgentAction(params: {
  subproject_id: string
  action_type: 'task' | 'note'
  title: string
  description?: string
  content?: string
}): Promise<Task | Note> {
  return request<Task | Note>('/api/agent/action', {
    method: 'POST',
    body: JSON.stringify(params),
  })
}

// ── Subproject Detail ──────────────────────────────────────────

export function getSubprojectDetail(id: string): Promise<SubprojectDetail> {
  return request<SubprojectDetail>(`/api/subprojects/${id}`)
}

export function getSubprojectFiles(id: string): Promise<FileTreeResponse> {
  return request<FileTreeResponse>(`/api/subprojects/${id}/files`)
}

export function getFileContent(subprojectId: string, path: string): Promise<FileContentResponse> {
  return request<FileContentResponse>(`/api/subprojects/${subprojectId}/files/${path}`)
}

// ── Search ─────────────────────────────────────────────────────

export interface SearchResult {
  entity_type: string
  entity_id: string
  title: string
  snippet: string
  parent_id: string
}

export interface SearchResponse {
  query: string
  total: number
  results: SearchResult[]
  grouped: Record<string, SearchResult[]>
}

export function searchAll(q: string, types?: string): Promise<SearchResponse> {
  const params = new URLSearchParams({ q })
  if (types) params.set('types', types)
  return request<SearchResponse>(`/api/search?${params}`)
}

export function rebuildSearchIndex(): Promise<{ status: string; indexed: number }> {
  return request<{ status: string; indexed: number }>('/api/search/rebuild', { method: 'POST' })
}

// ── Execution ──────────────────────────────────────────────────

export interface ExecResponse {
  id: string
  action: string
  command: string
  exit_code: number
  stdout: string
  stderr: string
  duration_ms: number
  timed_out: boolean
  working_dir: string
  ecosystem: string
}

export interface ExecHistoryEntry {
  id: string
  command: string
  action_type: string
  exit_code: number
  duration_ms: number
  started_at: string
}

export function executeInSubproject(
  subprojectId: string,
  action: string,
  command = '',
  timeout = 60,
): Promise<ExecResponse> {
  return request<ExecResponse>(`/api/subprojects/${subprojectId}/exec`, {
    method: 'POST',
    body: JSON.stringify({ action, command, timeout }),
  })
}

export function getExecHistory(subprojectId: string): Promise<ExecHistoryEntry[]> {
  return request<ExecHistoryEntry[]>(`/api/subprojects/${subprojectId}/exec/history`)
}

export function getEcosystem(subprojectId: string): Promise<{
  ecosystem: string
  workspace_exists: boolean
  workspace_path?: string
  files?: string[]
}> {
  return request(`/api/subprojects/${subprojectId}/ecosystem`)
}

// ── Providers ──────────────────────────────────────────────────

export interface ProviderInfo {
  id: string
  name: string
  status: string
  models: Array<{ name: string; size_gb?: number }>
  requires: string
  configured: boolean
}

export interface ProvidersResponse {
  providers: ProviderInfo[]
  active_provider: string
  active_model: string
  recommended: string
  mode: string
  setup_hint: string
}

export function getProviders(): Promise<ProvidersResponse> {
  return request<ProvidersResponse>('/api/system/providers')
}
