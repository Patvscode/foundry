import clsx from 'clsx'

type Status = 'healthy' | 'degraded' | 'error'

interface StatusBadgeProps {
  status: Status
  label: string
}

const statusDotClass: Record<Status, string> = {
  healthy: 'bg-emerald-500',
  degraded: 'bg-amber-500',
  error: 'bg-red-500',
}

export function StatusBadge({ status, label }: StatusBadgeProps) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900 px-3 py-1 text-sm text-zinc-200">
      <span className={clsx('size-2 rounded-full', statusDotClass[status])} aria-hidden="true" />
      {label}
    </span>
  )
}
