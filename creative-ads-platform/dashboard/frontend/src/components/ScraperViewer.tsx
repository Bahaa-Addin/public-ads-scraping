/**
 * ScraperViewer - Live video viewer for a single scraper session
 */

import { useState } from 'react'
import { Maximize2, Minimize2, Wifi, WifiOff, Loader, Clock, Camera } from 'lucide-react'
import { useScraperStream, StreamStatus } from '@/hooks/useScraperStream'
import { cn } from '@/lib/utils'

interface ScraperViewerProps {
  sessionId: string
  title?: string
  className?: string
  onExpand?: () => void
  isExpanded?: boolean
}

function StatusBadge({ status }: { status: StreamStatus }) {
  const statusConfig: Record<StreamStatus, { label: string; className: string; icon: React.ReactNode }> = {
    connecting: {
      label: 'Connecting',
      className: 'bg-warning-500/20 text-warning-400 border-warning-500/30',
      icon: <Loader className="w-3 h-3 animate-spin" />,
    },
    connected: {
      label: 'Connected',
      className: 'bg-brand-500/20 text-brand-400 border-brand-500/30',
      icon: <Wifi className="w-3 h-3" />,
    },
    waiting: {
      label: 'Waiting',
      className: 'bg-surface-600/50 text-surface-300 border-surface-500/30',
      icon: <Clock className="w-3 h-3" />,
    },
    live: {
      label: 'Live',
      className: 'bg-success-500/20 text-success-400 border-success-500/30 animate-pulse',
      icon: <Camera className="w-3 h-3" />,
    },
    ended: {
      label: 'Ended',
      className: 'bg-surface-600/50 text-surface-400 border-surface-500/30',
      icon: null,
    },
    disconnected: {
      label: 'Disconnected',
      className: 'bg-surface-700/50 text-surface-500 border-surface-600/30',
      icon: <WifiOff className="w-3 h-3" />,
    },
    error: {
      label: 'Error',
      className: 'bg-danger-500/20 text-danger-400 border-danger-500/30',
      icon: <WifiOff className="w-3 h-3" />,
    },
  }

  const config = statusConfig[status]

  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border',
      config.className
    )}>
      {config.icon}
      {config.label}
    </span>
  )
}

export function ScraperViewer({
  sessionId,
  title,
  className,
  onExpand,
  isExpanded = false,
}: ScraperViewerProps) {
  const { frame, status, sessionInfo, frameCount, error, reconnect } = useScraperStream(sessionId)
  const [showOverlay, setShowOverlay] = useState(true)

  const displayTitle = title || sessionInfo?.source || sessionId

  return (
    <div
      className={cn(
        'relative rounded-lg overflow-hidden bg-surface-900 border border-surface-700',
        className
      )}
    >
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between p-2 bg-gradient-to-b from-black/80 to-transparent">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-white truncate max-w-[200px]">
            {displayTitle}
          </span>
          <StatusBadge status={status} />
        </div>
        
        <div className="flex items-center gap-1">
          {frameCount > 0 && (
            <span className="text-xs text-surface-400 mr-2">
              {frameCount} frames
            </span>
          )}
          {onExpand && (
            <button
              onClick={onExpand}
              className="p-1 rounded hover:bg-white/10 transition-colors"
            >
              {isExpanded ? (
                <Minimize2 className="w-4 h-4 text-white" />
              ) : (
                <Maximize2 className="w-4 h-4 text-white" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Video Frame */}
      <div 
        className="aspect-video bg-surface-950 flex items-center justify-center"
        onClick={() => setShowOverlay(!showOverlay)}
      >
        {frame ? (
          <img
            src={frame}
            alt="Scraper view"
            className="w-full h-full object-contain"
          />
        ) : (
          <div className="text-center text-surface-500">
            {status === 'connecting' && (
              <>
                <Loader className="w-8 h-8 mx-auto mb-2 animate-spin" />
                <p>Connecting to stream...</p>
              </>
            )}
            {status === 'waiting' && (
              <>
                <Clock className="w-8 h-8 mx-auto mb-2" />
                <p>Waiting for scraper to start...</p>
              </>
            )}
            {status === 'disconnected' && (
              <>
                <WifiOff className="w-8 h-8 mx-auto mb-2" />
                <p>Stream disconnected</p>
                <button
                  onClick={reconnect}
                  className="mt-2 text-sm text-brand-400 hover:text-brand-300"
                >
                  Reconnect
                </button>
              </>
            )}
            {status === 'error' && (
              <>
                <WifiOff className="w-8 h-8 mx-auto mb-2 text-danger-400" />
                <p className="text-danger-400">{error || 'Connection error'}</p>
                <button
                  onClick={reconnect}
                  className="mt-2 text-sm text-brand-400 hover:text-brand-300"
                >
                  Try Again
                </button>
              </>
            )}
            {status === 'ended' && (
              <>
                <Camera className="w-8 h-8 mx-auto mb-2" />
                <p>Stream ended</p>
                {sessionInfo && (
                  <p className="text-xs text-surface-600 mt-1">
                    {sessionInfo.screenshot_count} screenshots captured
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </div>

      {/* Footer overlay with URL */}
      {showOverlay && sessionInfo?.current_url && (
        <div className="absolute bottom-0 left-0 right-0 z-10 p-2 bg-gradient-to-t from-black/80 to-transparent">
          <p className="text-xs text-surface-300 truncate">
            {sessionInfo.current_url}
          </p>
        </div>
      )}
    </div>
  )
}

export default ScraperViewer
