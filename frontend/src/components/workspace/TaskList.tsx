import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'

import type { Task } from '@/api/client'
import { createTask, getTasks, updateTask } from '@/api/client'

interface TaskListProps {
  subprojectId: string
}

export function TaskList({ subprojectId }: TaskListProps) {
  const queryClient = useQueryClient()
  const [newTitle, setNewTitle] = useState('')

  const tasks = useQuery({
    queryKey: ['tasks', subprojectId],
    queryFn: () => getTasks(subprojectId),
  })

  const addMut = useMutation({
    mutationFn: (title: string) => createTask(subprojectId, title),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', subprojectId] })
      setNewTitle('')
    },
  })

  const toggleMut = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: string }) =>
      updateTask(subprojectId, taskId, { status }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks', subprojectId] }),
  })

  const handleAdd = () => {
    const trimmed = newTitle.trim()
    if (!trimmed) return
    addMut.mutate(trimmed)
  }

  return (
    <div className="space-y-3">
      {/* Add task */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Add a task…"
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

      {/* Task list */}
      {tasks.data?.length ? (
        <div className="space-y-1">
          {tasks.data.map((task: Task) => (
            <div
              key={task.id}
              className="flex items-start gap-2 rounded-md border border-zinc-800 bg-zinc-950 px-3 py-2"
            >
              <input
                type="checkbox"
                checked={task.status === 'done'}
                onChange={() =>
                  toggleMut.mutate({
                    taskId: task.id,
                    status: task.status === 'done' ? 'todo' : 'done',
                  })
                }
                className="mt-0.5 size-4 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
              />
              <div className="min-w-0 flex-1">
                <div className={`text-sm ${task.status === 'done' ? 'text-zinc-500 line-through' : 'text-zinc-200'}`}>
                  {task.title}
                </div>
                {task.description && (
                  <div className="mt-0.5 text-xs text-zinc-500">{task.description}</div>
                )}
              </div>
              <span className={`shrink-0 text-xs ${task.source === 'extracted' ? 'text-blue-400' : 'text-zinc-600'}`}>
                {task.source === 'extracted' ? 'auto' : 'manual'}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-zinc-500">No tasks yet.</p>
      )}
    </div>
  )
}
