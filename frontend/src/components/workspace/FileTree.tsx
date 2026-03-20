import { File, Folder, FolderOpen } from 'lucide-react'
import { useState } from 'react'

import type { FileEntry } from '@/api/client'

interface FileTreeProps {
  entries: FileEntry[]
  selectedPath: string | null
  onSelect: (path: string) => void
}

interface TreeNode {
  entry: FileEntry
  children: TreeNode[]
}

function buildTree(entries: FileEntry[]): TreeNode[] {
  const roots: TreeNode[] = []
  const nodeMap = new Map<string, TreeNode>()

  for (const entry of entries) {
    const node: TreeNode = { entry, children: [] }
    nodeMap.set(entry.path, node)

    const parts = entry.path.split('/')
    if (parts.length <= 1) {
      roots.push(node)
    } else {
      const parentPath = parts.slice(0, -1).join('/')
      const parent = nodeMap.get(parentPath)
      if (parent) {
        parent.children.push(node)
      } else {
        roots.push(node)
      }
    }
  }

  return roots
}

function TreeItem({ node, depth, selectedPath, onSelect }: {
  node: TreeNode
  depth: number
  selectedPath: string | null
  onSelect: (path: string) => void
}) {
  const [open, setOpen] = useState(depth < 1)
  const isDir = node.entry.is_dir
  const isSelected = node.entry.path === selectedPath

  return (
    <div>
      <button
        type="button"
        onClick={() => isDir ? setOpen(!open) : onSelect(node.entry.path)}
        className={`flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-xs transition-colors ${
          isSelected ? 'bg-blue-500/20 text-blue-300' : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200'
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {isDir ? (
          open ? <FolderOpen size={13} className="shrink-0 text-zinc-500" /> : <Folder size={13} className="shrink-0 text-zinc-500" />
        ) : (
          <File size={13} className="shrink-0 text-zinc-600" />
        )}
        <span className="truncate">{node.entry.name}</span>
        {!isDir && node.entry.size !== undefined && (
          <span className="ml-auto shrink-0 text-zinc-600">{formatSize(node.entry.size)}</span>
        )}
      </button>
      {isDir && open && node.children.map((child) => (
        <TreeItem key={child.entry.path} node={child} depth={depth + 1} selectedPath={selectedPath} onSelect={onSelect} />
      ))}
    </div>
  )
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}K`
  return `${(bytes / (1024 * 1024)).toFixed(1)}M`
}

export function FileTree({ entries, selectedPath, onSelect }: FileTreeProps) {
  const tree = buildTree(entries)

  if (tree.length === 0) {
    return <p className="text-xs text-zinc-500">Empty workspace</p>
  }

  return (
    <div className="space-y-0.5">
      {tree.map((node) => (
        <TreeItem key={node.entry.path} node={node} depth={0} selectedPath={selectedPath} onSelect={onSelect} />
      ))}
    </div>
  )
}
