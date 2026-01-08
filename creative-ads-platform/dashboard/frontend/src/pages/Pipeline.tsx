import { useState } from 'react'
import {
  Play,
  Pause,
  Trash2,
  Wifi,
  WifiOff,
  Zap,
  Image,
  Sparkles,
  FileText,
  Tag,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  ChevronDown,
  RefreshCw,
  Monitor,
  Film,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { ScraperGrid } from '@/components/ScraperGrid'
import { JobReplayPlayer } from '@/components/JobReplayPlayer'
import { useEventStream, PipelineEvent } from '@/hooks/useEventStream'
import { useJobsWithScreenshots } from '@/hooks/useJobScreenshots'
import { useIsTemplateMode } from '@/lib/useTemplateMode'
import { cn } from '@/lib/utils'
import { useMutation } from '@tanstack/react-query'
import * as api from '@/lib/api'

// Source options for scraping
const SOURCES = [
  { id: 'meta_ad_library', name: 'Meta Ad Library' },
  { id: 'google_ads_transparency', name: 'Google Ads Transparency' },
  { id: 'internet_archive', name: 'Internet Archive' },
  { id: 'wikimedia_commons', name: 'Wikimedia Commons' },
]

// Get icon and color for event type
function getEventStyle(type: string) {
  switch (type) {
    case 'pipeline_started':
      return { icon: Play, color: 'text-brand-500', bg: 'bg-brand-500/10' }
    case 'step_started':
      return { icon: Loader2, color: 'text-yellow-500', bg: 'bg-yellow-500/10' }
    case 'step_progress':
      return { icon: RefreshCw, color: 'text-blue-500', bg: 'bg-blue-500/10' }
    case 'asset_scraped':
      return { icon: Image, color: 'text-cyan-500', bg: 'bg-cyan-500/10' }
    case 'screenshot_captured':
      return { icon: Image, color: 'text-purple-500', bg: 'bg-purple-500/10' }
    case 'features_extracted':
      return { icon: Sparkles, color: 'text-pink-500', bg: 'bg-pink-500/10' }
    case 'prompt_generated':
      return { icon: FileText, color: 'text-green-500', bg: 'bg-green-500/10' }
    case 'step_completed':
      return { icon: CheckCircle, color: 'text-emerald-500', bg: 'bg-emerald-500/10' }
    case 'pipeline_completed':
      return { icon: CheckCircle, color: 'text-emerald-500', bg: 'bg-emerald-500/10' }
    case 'error':
      return { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10' }
    case 'connected':
      return { icon: Wifi, color: 'text-emerald-500', bg: 'bg-emerald-500/10' }
    default:
      return { icon: AlertCircle, color: 'text-surface-400', bg: 'bg-surface-800' }
  }
}

// Format timestamp
function formatTime(timestamp: string) {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  } catch {
    return '--:--:--'
  }
}

// Timeline Event Component
function TimelineEvent({ event }: { event: PipelineEvent }) {
  const style = getEventStyle(event.type)
  const Icon = style.icon
  const [expanded, setExpanded] = useState(false)

  const title = event.type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  const message = (event.data.message as string) || ''
  const hasDetails = Object.keys(event.data).length > 1 || event.data.image_url || event.data.screenshot_url

  return (
    <div className="flex gap-4 group">
      {/* Timeline line and dot */}
      <div className="flex flex-col items-center">
        <div className={cn('w-10 h-10 rounded-full flex items-center justify-center', style.bg)}>
          <Icon className={cn('w-5 h-5', style.color, event.type === 'step_started' && 'animate-spin')} />
        </div>
        <div className="w-px flex-1 bg-surface-700 group-last:hidden" />
      </div>

      {/* Event content */}
      <div className="flex-1 pb-6">
        <div className="flex items-start justify-between">
          <div>
            <p className={cn('font-medium', style.color)}>{title}</p>
            {message && <p className="text-sm text-surface-400 mt-0.5">{message}</p>}
            {event.job_id && (
              <p className="text-xs text-surface-500 mt-1">Job: {event.job_id.slice(0, 8)}...</p>
            )}
          </div>
          <span className="text-xs text-surface-500">{formatTime(event.timestamp)}</span>
        </div>

        {/* Progress bar */}
        {event.type === 'step_progress' && typeof event.data.progress === 'number' && (
          <div className="mt-2 h-2 bg-surface-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-500 transition-all duration-300"
              style={{ width: `${event.data.progress}%` }}
            />
          </div>
        )}

        {/* Image preview */}
        {(event.data.image_url || event.data.screenshot_url) && (
          <div className="mt-3">
            <img
              src={(event.data.image_url || event.data.screenshot_url) as string}
              alt="Asset preview"
              className="rounded-lg max-w-xs max-h-48 object-cover border border-surface-700"
            />
          </div>
        )}

        {/* Expandable details */}
        {hasDetails && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 mt-2 text-xs text-surface-500 hover:text-surface-300"
          >
            <ChevronDown className={cn('w-3 h-3 transition-transform', expanded && 'rotate-180')} />
            {expanded ? 'Hide details' : 'Show details'}
          </button>
        )}

        {expanded && (
          <pre className="mt-2 p-3 bg-surface-800/50 rounded-lg text-xs text-surface-400 overflow-x-auto">
            {JSON.stringify(event.data, null, 2)}
          </pre>
        )}
      </div>
    </div>
  )
}

export default function Pipeline() {
  const isTemplate = useIsTemplateMode()
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  // Form state
  const [selectedSources, setSelectedSources] = useState<string[]>(['meta_ad_library'])
  const [query, setQuery] = useState('')
  const [limit, setLimit] = useState(50)
  const [activeTab, setActiveTab] = useState<'timeline' | 'live' | 'replays'>('timeline')
  const [selectedReplayJob, setSelectedReplayJob] = useState<string | null>(null)

  // SSE connection
  const { events, connected, paused, setPaused, clearEvents, reconnect } = useEventStream(
    `${apiUrl}/api/v1/events/stream`
  )

  // Jobs with screenshots (for replay)
  const { data: jobsWithScreenshots } = useJobsWithScreenshots()

  // Job mutations
  const pipelineMutation = useMutation({
    mutationFn: () =>
      api.startPipelineJob({
        sources: selectedSources,
        query: query || undefined,
        limit,
        skip_steps: [],
      }),
  })

  const scrapeMutation = useMutation({
    mutationFn: () =>
      api.startScrapeJob({
        sources: selectedSources,
        query: query || undefined,
        limit,
      }),
  })

  const extractMutation = useMutation({
    mutationFn: () => api.startExtractJob({ reprocess: false }),
  })

  const generateMutation = useMutation({
    mutationFn: () => api.startGenerateJob({ regenerate: false }),
  })

  const classifyMutation = useMutation({
    mutationFn: () => api.startClassifyJob({ reclassify: false }),
  })

  const isAnyLoading =
    pipelineMutation.isPending ||
    scrapeMutation.isPending ||
    extractMutation.isPending ||
    generateMutation.isPending ||
    classifyMutation.isPending

  const toggleSource = (sourceId: string) => {
    setSelectedSources((prev) =>
      prev.includes(sourceId) ? prev.filter((s) => s !== sourceId) : [...prev, sourceId]
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Pipeline Control</h1>
          <p className="text-surface-400 mt-1">
            {isTemplate
              ? 'Preview pipeline controls with sample events'
              : 'Execute jobs and monitor pipeline progress in real-time'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {connected ? (
            <span className="flex items-center gap-2 text-sm text-emerald-500">
              <Wifi className="w-4 h-4" />
              Connected
            </span>
          ) : (
            <button
              onClick={reconnect}
              className="flex items-center gap-2 text-sm text-red-500 hover:text-red-400"
            >
              <WifiOff className="w-4 h-4" />
              Disconnected - Click to reconnect
            </button>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-brand-500" />
            Quick Actions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Source Selection */}
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">Sources</label>
              <div className="flex flex-wrap gap-2">
                {SOURCES.map((source) => (
                  <button
                    key={source.id}
                    onClick={() => toggleSource(source.id)}
                    className={cn(
                      'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                      selectedSources.includes(source.id)
                        ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                        : 'bg-surface-800 text-surface-400 border border-surface-700 hover:border-surface-600'
                    )}
                  >
                    {source.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Query and Limit */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-surface-300 mb-2">
                  Search Query (optional)
                </label>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="e.g., fintech, fashion, sports"
                  className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-white placeholder-surface-500 focus:outline-none focus:border-brand-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-surface-300 mb-2">
                  Limit
                </label>
                <input
                  type="number"
                  value={limit}
                  onChange={(e) => setLimit(Math.max(1, Math.min(500, Number(e.target.value))))}
                  min={1}
                  max={500}
                  className="w-full px-3 py-2 bg-surface-800 border border-surface-700 rounded-lg text-white focus:outline-none focus:border-brand-500"
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-wrap gap-3 pt-2">
              <button
                onClick={() => pipelineMutation.mutate()}
                disabled={isAnyLoading || selectedSources.length === 0 || isTemplate}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors',
                  'bg-brand-500 text-white hover:bg-brand-600',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                {pipelineMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                Run Full Pipeline
              </button>

              <button
                onClick={() => scrapeMutation.mutate()}
                disabled={isAnyLoading || selectedSources.length === 0 || isTemplate}
                className="flex items-center gap-2 px-3 py-2 rounded-lg font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Image className="w-4 h-4" />
                Scrape
              </button>

              <button
                onClick={() => extractMutation.mutate()}
                disabled={isAnyLoading || isTemplate}
                className="flex items-center gap-2 px-3 py-2 rounded-lg font-medium bg-pink-500/10 text-pink-400 border border-pink-500/20 hover:bg-pink-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Sparkles className="w-4 h-4" />
                Extract
              </button>

              <button
                onClick={() => generateMutation.mutate()}
                disabled={isAnyLoading || isTemplate}
                className="flex items-center gap-2 px-3 py-2 rounded-lg font-medium bg-green-500/10 text-green-400 border border-green-500/20 hover:bg-green-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <FileText className="w-4 h-4" />
                Generate
              </button>

              <button
                onClick={() => classifyMutation.mutate()}
                disabled={isAnyLoading || isTemplate}
                className="flex items-center gap-2 px-3 py-2 rounded-lg font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Tag className="w-4 h-4" />
                Classify
              </button>
            </div>

            {/* Status messages */}
            {(pipelineMutation.isSuccess ||
              scrapeMutation.isSuccess ||
              extractMutation.isSuccess ||
              generateMutation.isSuccess ||
              classifyMutation.isSuccess) && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
                Job created successfully! Watch the timeline below for progress.
              </div>
            )}

            {isTemplate && (
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm">
                Actions are disabled in template mode. Switch to the live dashboard to execute real jobs.
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Tab Selector */}
      <div className="flex items-center gap-1 p-1 bg-surface-800 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('timeline')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
            activeTab === 'timeline'
              ? 'bg-surface-700 text-white'
              : 'text-surface-400 hover:text-surface-300'
          )}
        >
          <Clock className="w-4 h-4" />
          Timeline
          {events.length > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-surface-600 text-xs">
              {events.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('live')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
            activeTab === 'live'
              ? 'bg-surface-700 text-white'
              : 'text-surface-400 hover:text-surface-300'
          )}
        >
          <Monitor className="w-4 h-4" />
          Live View
        </button>
        <button
          onClick={() => setActiveTab('replays')}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors',
            activeTab === 'replays'
              ? 'bg-surface-700 text-white'
              : 'text-surface-400 hover:text-surface-300'
          )}
        >
          <Film className="w-4 h-4" />
          Replays
          {jobsWithScreenshots && jobsWithScreenshots.count > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-surface-600 text-xs">
              {jobsWithScreenshots.count}
            </span>
          )}
        </button>
      </div>

      {/* Live Timeline Tab */}
      {activeTab === 'timeline' && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-brand-500" />
                Live Timeline
                {events.length > 0 && (
                  <span className="ml-2 px-2 py-0.5 rounded-full bg-surface-800 text-surface-400 text-xs">
                    {events.length} events
                  </span>
                )}
              </CardTitle>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPaused(!paused)}
                  className={cn(
                    'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
                    paused
                      ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                      : 'bg-surface-800 text-surface-400 border border-surface-700 hover:border-surface-600'
                  )}
                >
                  {paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
                  {paused ? 'Resume' : 'Pause'}
                </button>
                <button
                  onClick={clearEvents}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-surface-800 text-surface-400 border border-surface-700 hover:border-surface-600 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Clear
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {events.length === 0 ? (
              <div className="py-12 text-center">
                <div className="w-16 h-16 mx-auto rounded-full bg-surface-800 flex items-center justify-center mb-4">
                  <Clock className="w-8 h-8 text-surface-600" />
                </div>
                <p className="text-surface-400 font-medium">No events yet</p>
                <p className="text-surface-500 text-sm mt-1">
                  Start a job to see real-time progress here
                </p>
              </div>
            ) : (
              <div className="max-h-[600px] overflow-y-auto pr-2">
                {events.map((event, index) => (
                  <TimelineEvent key={`${event.timestamp}-${index}`} event={event} />
                ))}
              </div>
            )}

            {/* Auto-scroll indicator */}
            {events.length > 0 && !paused && (
              <div className="text-center mt-4 text-xs text-surface-500">
                <span className="inline-flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  Auto-scroll enabled
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Live View Tab */}
      {activeTab === 'live' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Monitor className="w-5 h-5 text-brand-500" />
              Live Scraper View
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScraperGrid maxColumns={2} />
          </CardContent>
        </Card>
      )}

      {/* Replays Tab */}
      {activeTab === 'replays' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Film className="w-5 h-5 text-brand-500" />
              Job Replays
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedReplayJob ? (
              <div className="space-y-4">
                <button
                  onClick={() => setSelectedReplayJob(null)}
                  className="text-sm text-brand-400 hover:text-brand-300 flex items-center gap-1"
                >
                  ← Back to job list
                </button>
                <JobReplayPlayer jobId={selectedReplayJob} />
              </div>
            ) : (
              <div>
                {!jobsWithScreenshots || jobsWithScreenshots.count === 0 ? (
                  <div className="py-12 text-center">
                    <div className="w-16 h-16 mx-auto rounded-full bg-surface-800 flex items-center justify-center mb-4">
                      <Film className="w-8 h-8 text-surface-600" />
                    </div>
                    <p className="text-surface-400 font-medium">No replays available</p>
                    <p className="text-surface-500 text-sm mt-1">
                      Complete a scraping job to see its replay here
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-surface-400 mb-4">
                      {jobsWithScreenshots.count} job{jobsWithScreenshots.count !== 1 ? 's' : ''} with recorded screenshots
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                      {jobsWithScreenshots.jobs.map((jobId) => (
                        <button
                          key={jobId}
                          onClick={() => setSelectedReplayJob(jobId)}
                          className="p-4 rounded-lg bg-surface-800 border border-surface-700 hover:border-surface-600 text-left transition-colors"
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <Film className="w-4 h-4 text-brand-500" />
                            <span className="font-medium text-white">Job Replay</span>
                          </div>
                          <p className="text-xs text-surface-500 font-mono truncate">
                            {jobId}
                          </p>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
