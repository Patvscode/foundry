import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Bot, ListTodo, MessageSquare, Send, Sparkles, StickyNote } from 'lucide-react'
import { useRef, useState, useEffect } from 'react'

import {
  executeAgentAction,
  sendAgentMessage,
  type ChatResponse,
} from '@/api/client'

interface Message {
  role: 'user' | 'assistant'
  content: string
  is_synthetic?: boolean
  suggestions?: Array<{ type: 'task' | 'note'; title: string }>
}

interface AgentPanelProps {
  projectId?: string
  resourceId?: string
  subprojectId?: string
  expanded: boolean
}

const QUICK_ACTIONS = [
  { label: 'Explain this', prompt: 'Explain what this is and what it contains.', icon: MessageSquare },
  { label: 'Suggest tasks', prompt: 'Suggest 3-5 concrete next tasks for this subproject. Format each as [TASK] title.', icon: ListTodo },
  { label: 'Summarize source', prompt: 'Summarize the source material this came from.', icon: StickyNote },
]

export function AgentPanel({ projectId, resourceId, subprojectId, expanded }: AgentPanelProps) {
  const queryClient = useQueryClient()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  // Reset session when context changes
  useEffect(() => {
    setMessages([])
    setSessionId(null)
  }, [projectId, resourceId, subprojectId])

  const chatMut = useMutation({
    mutationFn: (message: string) =>
      sendAgentMessage({
        message,
        session_id: sessionId ?? undefined,
        project_id: projectId,
        resource_id: resourceId,
        subproject_id: subprojectId,
      }),
    onSuccess: (data: ChatResponse) => {
      setSessionId(data.session_id)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.message,
          is_synthetic: data.is_synthetic,
          suggestions: data.suggestions,
        },
      ])
    },
  })

  const actionMut = useMutation({
    mutationFn: (params: { type: 'task' | 'note'; title: string }) =>
      executeAgentAction({
        subproject_id: subprojectId!,
        action_type: params.type,
        title: params.title,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', subprojectId] })
      queryClient.invalidateQueries({ queryKey: ['notes', subprojectId] })
    },
  })

  const handleSend = (text?: string) => {
    const msg = (text ?? input).trim()
    if (!msg) return
    setMessages((prev) => [...prev, { role: 'user', content: msg }])
    setInput('')
    chatMut.mutate(msg)
  }

  if (!expanded) return null

  const contextLabel = subprojectId ? 'subproject' : resourceId ? 'resource' : projectId ? 'project' : 'general'

  return (
    <div className="flex h-full max-h-[50vh] flex-col rounded-t-lg border border-zinc-800 bg-zinc-900">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-zinc-800 px-4 py-2">
        <Bot size={16} className="text-blue-400" />
        <span className="text-sm font-medium text-zinc-200">Agent</span>
        <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">{contextLabel}</span>
      </div>

      {/* Quick actions */}
      {messages.length === 0 && (
        <div className="flex flex-wrap gap-2 border-b border-zinc-800 px-4 py-3">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              type="button"
              onClick={() => handleSend(action.prompt)}
              disabled={chatMut.isPending}
              className="inline-flex items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-800 px-2.5 py-1.5 text-xs text-zinc-300 transition-colors hover:bg-zinc-700 hover:text-zinc-100 disabled:opacity-50"
            >
              <action.icon size={13} />
              {action.label}
            </button>
          ))}
        </div>
      )}

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-auto px-4 py-3 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                msg.role === 'user'
                  ? 'bg-blue-500/20 text-blue-100'
                  : 'bg-zinc-800 text-zinc-300'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.is_synthetic && (
                <p className="mt-1 text-xs text-amber-400">⚠ No LLM available — showing stored data</p>
              )}
              {/* Suggestion action buttons */}
              {msg.suggestions && msg.suggestions.length > 0 && subprojectId && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {msg.suggestions.map((s, si) => (
                    <button
                      key={si}
                      type="button"
                      onClick={() => actionMut.mutate({ type: s.type, title: s.title })}
                      disabled={actionMut.isPending}
                      className="inline-flex items-center gap-1 rounded bg-zinc-700 px-2 py-0.5 text-xs text-zinc-300 hover:bg-zinc-600 disabled:opacity-50"
                    >
                      {s.type === 'task' ? <ListTodo size={11} /> : <StickyNote size={11} />}
                      Add: {s.title.slice(0, 40)}{s.title.length > 40 ? '…' : ''}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {chatMut.isPending && (
          <div className="flex justify-start">
            <div className="rounded-lg bg-zinc-800 px-3 py-2 text-sm text-zinc-500">
              <Sparkles size={14} className="inline animate-pulse" /> Thinking…
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="flex gap-2 border-t border-zinc-800 px-4 py-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder="Ask the agent…"
          disabled={chatMut.isPending}
          className="h-9 flex-1 rounded-md border border-zinc-800 bg-zinc-950 px-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50 disabled:opacity-50"
        />
        <button
          type="button"
          onClick={() => handleSend()}
          disabled={chatMut.isPending || !input.trim()}
          className="rounded-md bg-blue-500 px-3 py-2 text-white transition-colors hover:bg-blue-400 disabled:opacity-50"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}
