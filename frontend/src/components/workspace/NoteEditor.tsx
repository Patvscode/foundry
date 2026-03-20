import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'

import type { Note } from '@/api/client'
import { createNote, deleteNote, getNotes, updateNote } from '@/api/client'

interface NoteEditorProps {
  subprojectId: string
}

export function NoteEditor({ subprojectId }: NoteEditorProps) {
  const queryClient = useQueryClient()
  const [newTitle, setNewTitle] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')

  const notes = useQuery({
    queryKey: ['notes', subprojectId],
    queryFn: () => getNotes(subprojectId),
  })

  const addMut = useMutation({
    mutationFn: (title: string) => createNote(subprojectId, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', subprojectId] })
      setNewTitle('')
    },
  })

  const saveMut = useMutation({
    mutationFn: ({ noteId, content }: { noteId: string; content: string }) =>
      updateNote(subprojectId, noteId, { content }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', subprojectId] })
      setEditingId(null)
    },
  })

  const deleteMut = useMutation({
    mutationFn: (noteId: string) => deleteNote(subprojectId, noteId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notes', subprojectId] }),
  })

  const handleAdd = () => {
    const trimmed = newTitle.trim()
    if (!trimmed) return
    addMut.mutate(trimmed)
  }

  const startEdit = (note: Note) => {
    setEditingId(note.id)
    setEditContent(note.content || '')
  }

  return (
    <div className="space-y-3">
      {/* Add note */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="New note title…"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
          className="h-8 flex-1 rounded-md border border-zinc-800 bg-zinc-950 px-2 text-xs text-zinc-100 placeholder:text-zinc-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
        />
        <button
          type="button"
          onClick={handleAdd}
          disabled={addMut.isPending}
          className="inline-flex items-center gap-1 rounded-md bg-blue-500 px-2 py-1 text-xs font-medium text-white hover:bg-blue-400 disabled:opacity-50"
        >
          <Plus size={12} />
          Add
        </button>
      </div>

      {/* Notes list */}
      {notes.data?.length ? (
        <div className="space-y-2">
          {notes.data.map((note: Note) => (
            <div key={note.id} className="rounded-lg border border-zinc-800 bg-zinc-950 p-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium text-zinc-200">{note.title}</h4>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => deleteMut.mutate(note.id)}
                    className="rounded p-1 text-zinc-600 transition-colors hover:bg-zinc-800 hover:text-red-400"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              </div>
              {editingId === note.id ? (
                <div className="mt-2 space-y-2">
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows={4}
                    className="w-full rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs text-zinc-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50"
                  />
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => saveMut.mutate({ noteId: note.id, content: editContent })}
                      className="rounded-md bg-blue-500 px-2 py-1 text-xs text-white hover:bg-blue-400"
                    >
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingId(null)}
                      className="text-xs text-zinc-500 hover:text-zinc-300"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  onClick={() => startEdit(note)}
                  className="mt-1 cursor-pointer text-xs text-zinc-400 hover:text-zinc-300"
                >
                  {note.content || 'Click to add content…'}
                </div>
              )}
              <div className="mt-1 text-xs text-zinc-600">
                {note.created_at ? new Date(note.created_at).toLocaleDateString() : ''}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-zinc-500">No notes yet.</p>
      )}
    </div>
  )
}
