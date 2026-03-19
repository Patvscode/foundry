import clsx from 'clsx'

const STAGES = ['extract', 'analyze', 'discover'] as const

type PipelineStage = (typeof STAGES)[number]

// Map pipeline_status values to the stage they represent
const STATUS_TO_STAGE: Record<string, { stage: PipelineStage; done: boolean; failed: boolean }> = {
  pending: { stage: 'extract', done: false, failed: false },
  extracting: { stage: 'extract', done: false, failed: false },
  extracted: { stage: 'extract', done: true, failed: false },
  extract_failed: { stage: 'extract', done: false, failed: true },
  analyzing: { stage: 'analyze', done: false, failed: false },
  analyzed: { stage: 'analyze', done: true, failed: false },
  analyze_failed: { stage: 'analyze', done: false, failed: true },
  discovering: { stage: 'discover', done: false, failed: false },
  discovered: { stage: 'discover', done: true, failed: false },
  discover_failed: { stage: 'discover', done: false, failed: true },
}

interface PipelineStatusProps {
  status: string
}

export function PipelineStatus({ status }: PipelineStatusProps) {
  const info = STATUS_TO_STAGE[status] ?? { stage: 'extract', done: false, failed: false }
  const currentIdx = STAGES.indexOf(info.stage)

  return (
    <div className="flex items-center gap-1.5">
      {STAGES.map((stage, idx) => {
        const isCurrent = idx === currentIdx
        const isPast = idx < currentIdx
        const isFailed = isCurrent && info.failed
        const isActive = isCurrent && !info.done && !info.failed

        return (
          <div key={stage} className="flex items-center gap-1.5">
            <div
              className={clsx(
                'size-2.5 rounded-full transition-colors',
                isFailed && 'bg-red-500',
                isActive && 'bg-blue-500 animate-pulse',
                isPast && 'bg-emerald-500',
                isCurrent && info.done && 'bg-emerald-500',
                !isCurrent && !isPast && 'bg-zinc-700',
              )}
              title={`${stage}${isFailed ? ' (failed)' : isActive ? ' (running)' : isPast || (isCurrent && info.done) ? ' (done)' : ''}`}
            />
            {idx < STAGES.length - 1 && (
              <div className={clsx('h-px w-3', isPast ? 'bg-emerald-500/50' : 'bg-zinc-700')} />
            )}
          </div>
        )
      })}
      <span className="ml-1.5 text-xs text-zinc-500">{status.replace('_', ' ')}</span>
    </div>
  )
}
