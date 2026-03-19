import { create } from 'zustand'

export type AgentMode = 'explore' | 'builder' | 'full-override'

interface AppState {
  sidebarOpen: boolean
  agentPanelOpen: boolean
  currentProjectId: string | null
  agentMode: AgentMode
  setSidebarOpen: (open: boolean) => void
  toggleSidebar: () => void
  setAgentPanelOpen: (open: boolean) => void
  toggleAgentPanel: () => void
  setCurrentProjectId: (projectId: string | null) => void
  setAgentMode: (mode: AgentMode) => void
}

export const useAppStore = create<AppState>((set) => ({
  sidebarOpen: true,
  agentPanelOpen: false,
  currentProjectId: null,
  agentMode: 'explore',
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setAgentPanelOpen: (open) => set({ agentPanelOpen: open }),
  toggleAgentPanel: () => set((state) => ({ agentPanelOpen: !state.agentPanelOpen })),
  setCurrentProjectId: (projectId) => set({ currentProjectId: projectId }),
  setAgentMode: (mode) => set({ agentMode: mode }),
}))
