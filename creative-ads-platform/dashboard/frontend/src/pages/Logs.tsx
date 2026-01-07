import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
  Info,
  AlertTriangle,
  Bug,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  FileText,
} from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select } from '@/components/ui/Select'
import { SearchInput } from '@/components/ui/Input'
import { EmptyState } from '@/components/ui/EmptyState'
import { getLogs, getErrorLogs, getLogStats, type LogEntry } from '@/lib/api'
import { formatDate, getLogLevelColor, getLogLevelBg, cn } from '@/lib/utils'

const levelOptions = [
  { value: '', label: 'All Levels' },
  { value: 'debug', label: 'Debug' },
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'error', label: 'Error' },
  { value: 'critical', label: 'Critical' },
]

const LevelIcon = ({ level }: { level: string }) => {
  switch (level) {
    case 'error':
    case 'critical':
      return <AlertCircle className="w-4 h-4" />
    case 'warning':
      return <AlertTriangle className="w-4 h-4" />
    case 'debug':
      return <Bug className="w-4 h-4" />
    default:
      return <Info className="w-4 h-4" />
  }
}

export default function Logs() {
  const [page, setPage] = useState(1)
  const [showErrors, setShowErrors] = useState(false)
  const [filters, setFilters] = useState({
    level: '',
    source: '',
    search: '',
    job_id: '',
  })

  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['logs', page, filters, showErrors],
    queryFn: () =>
      showErrors
        ? getErrorLogs({ page, page_size: 50 })
        : getLogs({
            page,
            page_size: 50,
            level: filters.level || undefined,
            source: filters.source || undefined,
            search: filters.search || undefined,
            job_id: filters.job_id || undefined,
          }),
    refetchInterval: 10000,
  })

  const { data: stats } = useQuery({
    queryKey: ['logStats'],
    queryFn: getLogStats,
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Logs</h1>
          <p className="text-surface-400 mt-1">
            Search and filter application logs
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={showErrors ? 'danger' : 'secondary'}
            onClick={() => setShowErrors(!showErrors)}
          >
            <AlertCircle className="w-4 h-4" />
            Errors Only {stats?.by_level?.error && `(${stats.by_level.error})`}
          </Button>
          <Button variant="secondary" onClick={() => refetch()}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-4">
        {[
          { label: 'Total', value: stats?.total_logs || 0, color: 'text-white' },
          { label: 'Info', value: stats?.by_level?.info || 0, color: 'text-blue-400' },
          { label: 'Warning', value: stats?.by_level?.warning || 0, color: 'text-yellow-400' },
          { label: 'Error', value: stats?.by_level?.error || 0, color: 'text-red-400' },
          { label: 'Debug', value: stats?.by_level?.debug || 0, color: 'text-gray-400' },
        ].map((stat) => (
          <div key={stat.label} className="card p-4">
            <p className="text-xs text-surface-400">{stat.label}</p>
            <p className={cn('text-2xl font-bold mt-1', stat.color)}>
              {stat.value}
            </p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Select
              options={levelOptions}
              value={filters.level}
              onChange={(e) => setFilters({ ...filters, level: e.target.value })}
              placeholder="Filter by level"
            />
            <Select
              options={[
                { value: '', label: 'All Sources' },
                ...Object.keys(stats?.by_source || {}).map((s) => ({
                  value: s,
                  label: s.replace(/_/g, ' '),
                })),
              ]}
              value={filters.source}
              onChange={(e) => setFilters({ ...filters, source: e.target.value })}
            />
            <SearchInput
              value={filters.job_id}
              onChange={(e) => setFilters({ ...filters, job_id: e.target.value })}
              placeholder="Filter by Job ID"
            />
            <SearchInput
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              placeholder="Search logs..."
            />
          </div>
        </CardContent>
      </Card>

      {/* Logs List */}
      <Card>
        <div className="divide-y divide-surface-800">
          {isLoading ? (
            Array.from({ length: 10 }).map((_, i) => (
              <div key={i} className="p-4">
                <div className="animate-pulse space-y-2">
                  <div className="flex items-center gap-4">
                    <div className="skeleton w-16 h-4" />
                    <div className="skeleton w-32 h-4" />
                    <div className="skeleton w-24 h-4" />
                  </div>
                  <div className="skeleton h-4 w-full" />
                </div>
              </div>
            ))
          ) : !logs?.logs || logs.logs.length === 0 ? (
            <div className="py-12">
              <EmptyState
                icon={FileText}
                title={filters.level || filters.source || filters.search ? "No matching logs" : "No logs yet"}
                description={
                  filters.level || filters.source || filters.search
                    ? "Try adjusting your filters or search query"
                    : "Logs will appear here as the pipeline processes jobs"
                }
                size="md"
              />
            </div>
          ) : (
            logs?.logs.map((log, index) => (
              <LogItem key={index} log={log} />
            ))
          )}
        </div>

        {/* Pagination */}
        {logs && logs.total > 50 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-surface-800">
            <span className="text-sm text-surface-400">
              Showing {(page - 1) * 50 + 1} to {Math.min(page * 50, logs.total)} of{' '}
              {logs.total}
            </span>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <span className="text-sm text-white px-3">Page {page}</span>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setPage((p) => p + 1)}
                disabled={!logs.has_more}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

function LogItem({ log }: { log: LogEntry }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={cn(
        'p-4 cursor-pointer transition-colors hover:bg-surface-800/50',
        expanded && 'bg-surface-800/30'
      )}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start gap-3">
        {/* Level Icon */}
        <div
          className={cn(
            'shrink-0 p-1.5 rounded-lg mt-0.5',
            getLogLevelBg(log.level)
          )}
        >
          <div className={getLogLevelColor(log.level)}>
            <LevelIcon level={log.level} />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <span
              className={cn(
                'text-xs font-semibold uppercase',
                getLogLevelColor(log.level)
              )}
            >
              {log.level}
            </span>
            <span className="text-xs text-surface-500">
              {formatDate(log.timestamp)}
            </span>
            {log.source && (
              <span className="text-xs text-surface-400 px-2 py-0.5 rounded bg-surface-800">
                {log.source}
              </span>
            )}
            {log.job_id && (
              <span className="text-xs text-brand-400 font-mono">
                Job: {log.job_id.slice(0, 8)}
              </span>
            )}
            {log.asset_id && (
              <span className="text-xs text-purple-400 font-mono">
                Asset: {log.asset_id.slice(0, 8)}
              </span>
            )}
          </div>
          <p className="text-sm text-white mt-1">{log.message}</p>

          {/* Expanded Details */}
          {expanded && log.metadata && (
            <div className="mt-3 p-3 rounded-lg bg-surface-900 font-mono text-xs">
              <pre className="text-surface-300 overflow-x-auto">
                {JSON.stringify(log.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

