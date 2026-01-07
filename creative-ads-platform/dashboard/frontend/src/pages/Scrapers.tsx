import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Play,
  Pause,
  Power,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  TrendingUp,
  Zap,
  Radar,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import { EmptyState } from '@/components/ui/EmptyState'
import { getScraperStatuses, getScraperMetrics, triggerScraping, triggerAllScrapers } from '@/lib/api'
import { formatRelativeTime, formatSourceName, formatNumber, formatPercent, cn } from '@/lib/utils'

export default function Scrapers() {
  const queryClient = useQueryClient()
  const [selectedSources, setSelectedSources] = useState<string[]>([])
  const [scrapeQuery, setScrapeQuery] = useState('')
  const [maxItems, setMaxItems] = useState(100)

  const { data: statuses, isLoading } = useQuery({
    queryKey: ['scraperStatuses'],
    queryFn: getScraperStatuses,
    refetchInterval: 10000,
  })

  const { data: metrics } = useQuery({
    queryKey: ['scraperMetrics'],
    queryFn: getScraperMetrics,
    refetchInterval: 15000,
  })

  const triggerMutation = useMutation({
    mutationFn: () => triggerScraping(selectedSources, {
      query: scrapeQuery || undefined,
      max_items_per_source: maxItems,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scraperStatuses'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setSelectedSources([])
      setScrapeQuery('')
    },
  })

  const triggerAllMutation = useMutation({
    mutationFn: () => triggerAllScrapers({
      query: scrapeQuery || undefined,
      max_items_per_source: maxItems,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scraperStatuses'] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setScrapeQuery('')
    },
  })

  const toggleSource = (source: string) => {
    setSelectedSources((prev) =>
      prev.includes(source)
        ? prev.filter((s) => s !== source)
        : [...prev, source]
    )
  }

  const totalItems = statuses?.reduce((sum, s) => sum + s.items_scraped, 0) || 0
  const avgSuccessRate = statuses?.length
    ? statuses.reduce((sum, s) => sum + s.success_rate, 0) / statuses.length
    : 0
  const runningCount = statuses?.filter((s) => s.running).length || 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Scrapers</h1>
          <p className="text-surface-400 mt-1">
            Monitor and control web scrapers
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => triggerAllMutation.mutate()}
            loading={triggerAllMutation.isPending}
          >
            <Zap className="w-4 h-4" />
            Trigger All
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/20">
              <Power className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className="text-sm text-surface-400">Running</p>
              <p className="text-xl font-bold text-white">{runningCount}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/20">
              <TrendingUp className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-sm text-surface-400">Total Items</p>
              <p className="text-xl font-bold text-white">{formatNumber(totalItems)}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/20">
              <CheckCircle className="w-5 h-5 text-cyan-500" />
            </div>
            <div>
              <p className="text-sm text-surface-400">Avg Success Rate</p>
              <p className="text-xl font-bold text-white">{formatPercent(avgSuccessRate * 100)}</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/20">
              <RefreshCw className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <p className="text-sm text-surface-400">Sources</p>
              <p className="text-xl font-bold text-white">{statuses?.length || 0}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Trigger Panel */}
      <Card>
        <CardHeader>
          <CardTitle>Trigger Scraping Jobs</CardTitle>
          <CardDescription>
            Select sources and configure scraping parameters
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Source Selection */}
            <div>
              <label className="block text-sm font-medium text-surface-300 mb-2">
                Select Sources
              </label>
              <div className="flex flex-wrap gap-2">
                {statuses?.map((status) => (
                  <button
                    key={status.source}
                    onClick={() => toggleSource(status.source)}
                    className={cn(
                      'px-4 py-2 rounded-lg border transition-all',
                      selectedSources.includes(status.source)
                        ? 'bg-brand-500/20 border-brand-500 text-brand-400'
                        : 'border-surface-700 text-surface-400 hover:text-white hover:border-surface-600'
                    )}
                  >
                    {formatSourceName(status.source)}
                  </button>
                ))}
              </div>
            </div>

            {/* Options */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="Search Query (optional)"
                value={scrapeQuery}
                onChange={(e) => setScrapeQuery(e.target.value)}
                placeholder="e.g., fintech, SaaS"
              />
              <div>
                <label className="block text-sm font-medium text-surface-300 mb-1.5">
                  Max Items per Source
                </label>
                <Select
                  options={[
                    { value: '25', label: '25 items' },
                    { value: '50', label: '50 items' },
                    { value: '100', label: '100 items' },
                    { value: '200', label: '200 items' },
                    { value: '500', label: '500 items' },
                  ]}
                  value={maxItems.toString()}
                  onChange={(e) => setMaxItems(parseInt(e.target.value))}
                />
              </div>
            </div>

            {/* Trigger Button */}
            <div className="flex justify-end pt-4">
              <Button
                onClick={() => triggerMutation.mutate()}
                loading={triggerMutation.isPending}
                disabled={selectedSources.length === 0}
              >
                <Play className="w-4 h-4" />
                Start Scraping ({selectedSources.length} sources)
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Scraper Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="p-6">
              <div className="animate-pulse space-y-4">
                <div className="flex items-center gap-3">
                  <div className="skeleton w-12 h-12 rounded-lg" />
                  <div className="skeleton h-6 w-40" />
                </div>
                <div className="skeleton h-4 w-full" />
                <div className="skeleton h-4 w-3/4" />
              </div>
            </Card>
          ))
        ) : !statuses || statuses.length === 0 ? (
          <Card className="md:col-span-2 p-12">
            <EmptyState
              icon={Radar}
              title="No scrapers configured"
              description="Scraper sources will appear here when the backend is connected"
            />
          </Card>
        ) : (
          statuses.map((status) => (
            <ScraperCard key={status.source} status={status} />
          ))
        )}
      </div>
    </div>
  )
}

function ScraperCard({ status }: { status: { source: string; enabled: boolean; running: boolean; last_run?: string; items_scraped: number; success_rate: number; error_count: number; last_error?: string } }) {
  return (
    <Card className="p-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'w-12 h-12 rounded-lg flex items-center justify-center',
              status.running
                ? 'bg-green-500/20'
                : status.enabled
                ? 'bg-blue-500/20'
                : 'bg-surface-700'
            )}
          >
            {status.running ? (
              <RefreshCw className="w-6 h-6 text-green-500 animate-spin" />
            ) : (
              <Power
                className={cn(
                  'w-6 h-6',
                  status.enabled ? 'text-blue-500' : 'text-surface-500'
                )}
              />
            )}
          </div>
          <div>
            <h3 className="font-semibold text-white">
              {formatSourceName(status.source)}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <Badge
                variant={status.running ? 'success' : status.enabled ? 'info' : 'neutral'}
                dot
              >
                {status.running ? 'Running' : status.enabled ? 'Idle' : 'Disabled'}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-surface-400">Items Scraped</span>
          <span className="text-white font-medium">
            {formatNumber(status.items_scraped)}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-surface-400">Success Rate</span>
          <span
            className={cn(
              'font-medium',
              status.success_rate > 0.95
                ? 'text-green-500'
                : status.success_rate > 0.8
                ? 'text-yellow-500'
                : 'text-red-500'
            )}
          >
            {formatPercent(status.success_rate * 100)}
          </span>
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-surface-400">Last Run</span>
          <span className="text-white">
            {status.last_run ? formatRelativeTime(status.last_run) : 'Never'}
          </span>
        </div>
        {status.error_count > 0 && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-surface-400">Errors</span>
            <span className="text-red-500 font-medium">{status.error_count}</span>
          </div>
        )}
      </div>

      {status.last_error && (
        <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="text-xs">{status.last_error}</span>
          </div>
        </div>
      )}
    </Card>
  )
}

