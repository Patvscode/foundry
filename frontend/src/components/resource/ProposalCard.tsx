import { useState } from 'react'
import { Check, X, Pencil } from 'lucide-react'

import type { SubprojectProposal } from '@/api/client'

interface ProposalCardProps {
  proposal: SubprojectProposal & { decision?: string | null }
  index: number
  onAccept: (index: number, edits: { suggested_name?: string; description?: string; type?: string }) => void
  onReject: (index: number) => void
  disabled: boolean
}

export function ProposalCard({ proposal, index, onAccept, onReject, disabled }: ProposalCardProps) {
  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState(proposal.suggested_name)
  const [editDesc, setEditDesc] = useState(proposal.description)
  const [editType, setEditType] = useState(proposal.type)

  const isAccepted = proposal.decision === 'accepted'
  const isRejected = proposal.decision === 'rejected'

  const handleAccept = () => {
    const edits: Record<string, string> = {}
    if (editName !== proposal.suggested_name) edits.suggested_name = editName
    if (editDesc !== proposal.description) edits.description = editDesc
    if (editType !== proposal.type) edits.type = editType
    onAccept(index, edits)
    setEditing(false)
  }

  return (
    <div
      className={`rounded-lg border p-3 transition-colors ${
        isAccepted
          ? 'border-emerald-500/30 bg-emerald-500/5'
          : isRejected
            ? 'border-zinc-800 bg-zinc-950 opacity-50'
            : 'border-zinc-800 bg-zinc-950'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        {editing ? (
          <input
            type="text"
            value={editName}
            onChange={(e) => setEditName(e.target.value)}
            className="h-7 flex-1 rounded border border-zinc-700 bg-zinc-900 px-2 text-sm text-zinc-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
          />
        ) : (
          <span className="text-sm font-medium text-zinc-200">{proposal.suggested_name}</span>
        )}
        <span
          className={`text-xs ${
            proposal.confidence >= 0.7
              ? 'text-emerald-400'
              : proposal.confidence >= 0.3
                ? 'text-amber-400'
                : 'text-zinc-500'
          }`}
        >
          {Math.round(proposal.confidence * 100)}%
        </span>
      </div>

      {/* Description */}
      {editing ? (
        <textarea
          value={editDesc}
          onChange={(e) => setEditDesc(e.target.value)}
          rows={2}
          className="mt-2 w-full rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
        />
      ) : (
        <p className="mt-1 text-xs text-zinc-400">{proposal.description}</p>
      )}

      {/* Synthetic warning */}
      {proposal.is_synthetic && (
        <p className="mt-1 text-xs text-amber-400">⚠ Placeholder — no LLM available</p>
      )}

      {/* Type/complexity badges */}
      <div className="mt-2 flex items-center gap-2">
        {editing ? (
          <select
            value={editType}
            onChange={(e) => setEditType(e.target.value)}
            className="h-6 rounded border border-zinc-700 bg-zinc-900 px-1 text-xs text-zinc-300"
          >
            {['library', 'tool', 'model', 'dataset', 'service', 'research'].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        ) : (
          <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-xs text-zinc-400">
            {proposal.type}
          </span>
        )}
        <span className="rounded-full border border-zinc-700 px-2 py-0.5 text-xs text-zinc-400">
          {proposal.complexity}
        </span>
      </div>

      {/* Status / Actions */}
      <div className="mt-3 flex items-center gap-2">
        {isAccepted ? (
          <span className="text-xs text-emerald-400">✓ Accepted</span>
        ) : isRejected ? (
          <span className="text-xs text-zinc-500">✗ Rejected</span>
        ) : (
          <>
            <button
              type="button"
              onClick={handleAccept}
              disabled={disabled}
              className="inline-flex items-center gap-1 rounded-md bg-emerald-600 px-2 py-1 text-xs font-medium text-white transition-colors hover:bg-emerald-500 disabled:opacity-50"
            >
              <Check size={12} />
              Accept
            </button>
            <button
              type="button"
              onClick={() => onReject(index)}
              disabled={disabled}
              className="inline-flex items-center gap-1 rounded-md border border-zinc-700 px-2 py-1 text-xs text-zinc-300 transition-colors hover:bg-zinc-800 disabled:opacity-50"
            >
              <X size={12} />
              Reject
            </button>
            {!editing && (
              <button
                type="button"
                onClick={() => setEditing(true)}
                className="inline-flex items-center gap-1 rounded-md border border-zinc-700 px-2 py-1 text-xs text-zinc-300 transition-colors hover:bg-zinc-800"
              >
                <Pencil size={12} />
                Edit
              </button>
            )}
            {editing && (
              <button
                type="button"
                onClick={() => setEditing(false)}
                className="text-xs text-zinc-500 hover:text-zinc-300"
              >
                Cancel edit
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}
