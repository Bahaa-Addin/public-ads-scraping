/**
 * ScraperGrid - Multi-scraper grid view for monitoring multiple streams
 */

import { useState } from 'react'
import { Monitor, X, Maximize2 } from 'lucide-react'
import { ScraperViewer } from './ScraperViewer'
import { useActiveScrapers } from '@/hooks/useScraperStream'
import { cn } from '@/lib/utils'

interface ScraperGridProps {
  className?: string
  maxColumns?: number
}

export function ScraperGrid({ className, maxColumns = 2 }: ScraperGridProps) {
  const { sessions, loading, error } = useActiveScrapers(3000) // Poll every 3s
  const [expandedSession, setExpandedSession] = useState<string | null>(null)

  // Grid column classes based on session count and max columns
  const getGridClass = (count: number) => {
    if (count === 1) return 'grid-cols-1'
    if (count === 2) return maxColumns >= 2 ? 'grid-cols-2' : 'grid-cols-1'
    if (count === 3) return maxColumns >= 3 ? 'grid-cols-3' : 'grid-cols-2'
    return maxColumns >= 2 ? 'grid-cols-2' : 'grid-cols-1'
  }

  if (loading) {
    return (
      <div className={cn('flex items-center justify-center py-12', className)}>
        <div className="text-center text-surface-500">
          <Monitor className="w-8 h-8 mx-auto mb-2 animate-pulse" />
          <p>Loading active scrapers...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={cn('flex items-center justify-center py-12', className)}>
        <div className="text-center text-danger-400">
          <Monitor className="w-8 h-8 mx-auto mb-2" />
          <p>Failed to load active scrapers</p>
          <p className="text-xs text-surface-500 mt-1">{error}</p>
        </div>
      </div>
    )
  }

  if (sessions.length === 0) {
    return (
      <div className={cn('flex items-center justify-center py-12', className)}>
        <div className="text-center text-surface-500">
          <Monitor className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="text-lg font-medium mb-1">No Active Scrapers</p>
          <p className="text-sm">
            Start a scraping job to see the live browser view here.
          </p>
        </div>
      </div>
    )
  }

  // Expanded view - single scraper fullscreen
  if (expandedSession) {
    return (
      <div className={cn('relative', className)}>
        <button
          onClick={() => setExpandedSession(null)}
          className="absolute top-2 right-2 z-20 p-2 rounded-lg bg-surface-800/80 hover:bg-surface-700 transition-colors"
        >
          <X className="w-5 h-5 text-white" />
        </button>
        <ScraperViewer
          sessionId={expandedSession}
          className="w-full h-[600px]"
          isExpanded={true}
          onExpand={() => setExpandedSession(null)}
        />
      </div>
    )
  }

  // Grid view - multiple scrapers
  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Monitor className="w-5 h-5 text-brand-500" />
          <span className="text-sm font-medium text-white">
            {sessions.length} Active Scraper{sessions.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      {/* Grid */}
      <div className={cn('grid gap-4', getGridClass(sessions.length))}>
        {sessions.map((session) => (
          <ScraperViewer
            key={session.session_id}
            sessionId={session.session_id}
            title={session.source}
            onExpand={() => setExpandedSession(session.session_id)}
          />
        ))}
      </div>
    </div>
  )
}

/**
 * Compact scraper grid for embedding in other pages
 */
export function ScraperGridCompact({ className }: { className?: string }) {
  const { sessions } = useActiveScrapers(5000)

  if (sessions.length === 0) {
    return null
  }

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center gap-2 text-xs text-surface-400">
        <div className="w-2 h-2 rounded-full bg-success-500 animate-pulse" />
        {sessions.length} live stream{sessions.length !== 1 ? 's' : ''}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {sessions.slice(0, 2).map((session) => (
          <ScraperViewer
            key={session.session_id}
            sessionId={session.session_id}
            title={session.source}
            className="h-32"
          />
        ))}
      </div>
      {sessions.length > 2 && (
        <p className="text-xs text-surface-500 text-center">
          +{sessions.length - 2} more stream{sessions.length - 2 !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  )
}

export default ScraperGrid
