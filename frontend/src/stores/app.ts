import { create } from 'zustand'

export type AgentMode = 'explore' | 'builder' | 'full-override'

export interface AgentContext {
  projectId?: string
  resourceId?: string
  subprojectId?: string
}

interface AppState {
  sidebarOpen: boolean
  agentPanelOpen: boolean
  currentProjectId: string | null
  agentMode: AgentMode
  agentContext: AgentContext
  setSidebarOpen: (open: boolean) => void
  toggleSidebar: () => void
  setAgentPanelOpen: (open: boolean) => void
  toggleAgentPanel: () => void
  setCurrentProjectId: (projectId: string | null) => void
  setAgentMode: (mode: AgentMode) => void
  setAgentContext: (context: AgentContext) => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  agentPanelOpen: false,
  currentProjectId: null,
  agentMode: 'explore',
  agentContext: {},
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setAgentPanelOpen: (open) => set({ agentPanelOpen: open }),
  toggleAgentPanel: () => set((state) => ({ agentPanelOpen: !state.agentPanelOpen })),
  setCurrentProjectId: (projectId) => set({ currentProjectId: projectId }),
  setAgentMode: (mode) => set({ agentMode: mode }),
  setAgentContext: (context) => set({ agentContext: context }),
}))
