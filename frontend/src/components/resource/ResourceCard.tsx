import { Globe } from 'lucide-react'

import { PipelineStatus } from '@/components/resource/PipelineStatus'

interface ResourceCardProps {
  resource: {
    id: string
    url: string
    title: string | null
    type: string
    pipeline_status: string
  }
  selected: boolean
  onClick: () => void
}

export function ResourceCard({ resource, selected, onClick }: ResourceCardProps) {
  const isActive = !resource.pipeline_status.includes('failed') &&
    resource.pipeline_status !== 'discovered'

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full flex-col gap-2 rounded-lg border p-3 text-left transition-colors ${
        selected
          ? 'border-blue-500/50 bg-zinc-800'
          : 'border-zinc-800 bg-zinc-950 hover:border-zinc-700 hover:bg-zinc-900'
      }`}
    >
      <div className="flex items-center gap-2">
        <Globe size={14} className="shrink-0 text-zinc-400" />
        <span className="truncate text-sm text-zinc-200">
          {resource.title || resource.url}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <PipelineStatus status={resource.pipeline_status} />
        {isActive && (
          <span className="text-xs text-blue-400">processing…</span>
        )}
      </div>
    </button>
  )
}
