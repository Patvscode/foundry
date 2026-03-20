import { useEffect, useState } from 'react'
import { Sidebar } from './Sidebar'
import { CommandPalette } from '@/components/common/CommandPalette'

export function Shell({ children }: { children: React.ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setPaletteOpen((v) => !v)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100">
      <Sidebar onOpenPalette={() => setPaletteOpen(true)} />
      <main className="flex-1 overflow-auto p-4">{children}</main>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  )
}
