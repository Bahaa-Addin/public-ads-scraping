import {
  Image,
  Sparkles,
  MessageSquare,
  AlertCircle,
  Clock,
  Activity,
  TrendingUp,
  Zap,
  BarChart3,
  PieChartIcon,
  ListTodo,
  Play,
  ArrowRight
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { StatCard } from '@/components/ui/StatCard';
import { StatusBadge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import {
  useDashboardMetrics,
  useRecentJobs,
  useIndustryDistribution,
  useTimeSeries
} from '@/lib/useDataHooks';
import { useIsTemplateMode } from '@/lib/useTemplateMode';
import {
  formatNumber,
  formatDuration,
  formatRelativeTime,
  INDUSTRY_COLORS,
  formatIndustryName
} from '@/lib/utils';
import {
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { format, parseISO } from 'date-fns';

export default function Dashboard() {
  const isTemplate = useIsTemplateMode();

  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics();
  const { data: recentJobs, isLoading: jobsLoading } = useRecentJobs(5);
  const { data: industryData, isLoading: industryLoading } = useIndustryDistribution();
  const { data: throughputData, isLoading: throughputLoading } = useTimeSeries(
    'assets_scraped',
    24
  );

  // Format time series data for Recharts
  const chartData =
    throughputData?.data?.map((point) => ({
      time: format(parseISO(point.timestamp), 'HH:mm'),
      value: point.value
    })) || [];

  // Format pie chart data
  const pieData =
    industryData
      ?.filter((item) => item.count > 0)
      .slice(0, 8)
      .map((item) => ({
        name: formatIndustryName(item.industry),
        value: item.count,
        color: INDUSTRY_COLORS[item.industry] || '#6b7280'
      })) || [];

  // Check if we have any real data
  const hasAssets = (metrics?.pipeline?.assets_scraped ?? 0) > 0;
  const hasChartData = chartData.length > 0 && chartData.some((d) => d.value > 0);
  const hasPieData = pieData.length > 0 && pieData.some((d) => d.value > 0);
  const hasJobs = recentJobs?.jobs && recentJobs.jobs.length > 0;
  const hasQueueData =
    metrics?.queue &&
    (metrics.queue.pending_jobs > 0 ||
      metrics.queue.in_progress_jobs > 0 ||
      metrics.queue.completed_jobs > 0 ||
      metrics.queue.failed_jobs > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-surface-400 mt-1">
          {isTemplate
            ? 'Preview dashboard with sample data'
            : 'Monitor your agentic ads pipeline in real-time'}
        </p>
      </div>

      {/* Quick Actions Card - Live Mode Only */}
      {!isTemplate && (
        <Card className="border-brand-500/20 bg-gradient-to-r from-brand-500/5 to-cyan-500/5">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-brand-500/20 flex items-center justify-center">
                  <Zap className="w-6 h-6 text-brand-500" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Pipeline Control Center</h3>
                  <p className="text-sm text-surface-400">
                    Execute jobs and monitor progress in real-time
                  </p>
                </div>
              </div>
              <Link
                to="/pipeline"
                className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-brand-500 text-white font-medium hover:bg-brand-600 transition-colors"
              >
                <Play className="w-4 h-4" />
                Open Pipeline
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Assets Scraped"
          value={metrics?.pipeline?.assets_scraped ?? 0}
          icon={Image}
          color="blue"
          change={isTemplate && hasAssets ? 12.5 : undefined}
          changeLabel={isTemplate && hasAssets ? 'vs last week' : undefined}
          loading={metricsLoading}
        />
        <StatCard
          title="Features Extracted"
          value={metrics?.pipeline?.features_extracted ?? 0}
          icon={Sparkles}
          color="purple"
          change={isTemplate && hasAssets ? 8.3 : undefined}
          changeLabel={isTemplate && hasAssets ? 'vs last week' : undefined}
          loading={metricsLoading}
        />
        <StatCard
          title="Prompts Generated"
          value={metrics?.pipeline?.prompts_generated ?? 0}
          icon={MessageSquare}
          color="green"
          change={isTemplate && hasAssets ? 15.2 : undefined}
          changeLabel={isTemplate && hasAssets ? 'vs last week' : undefined}
          loading={metricsLoading}
        />
        <StatCard
          title="Error Rate"
          value={`${metrics?.system?.error_rate_percent?.toFixed(1) ?? 0}%`}
          icon={AlertCircle}
          color={(metrics?.system?.error_rate_percent ?? 0) > 5 ? 'red' : 'cyan'}
          change={isTemplate && hasAssets ? -2.1 : undefined}
          changeLabel={isTemplate && hasAssets ? 'vs last week' : undefined}
          loading={metricsLoading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Throughput Chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-brand-500" />
              Pipeline Throughput (24h)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              {throughputLoading ? (
                <div className="h-full flex items-center justify-center">
                  <div className="animate-pulse text-surface-500">Loading chart...</div>
                </div>
              ) : hasChartData ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis dataKey="time" stroke="#71717a" fontSize={12} tickLine={false} />
                    <YAxis stroke="#71717a" fontSize={12} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#27272a',
                        border: '1px solid #3f3f46',
                        borderRadius: '8px'
                      }}
                      labelStyle={{ color: '#fff' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#0ea5e9"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorValue)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState
                  icon={BarChart3}
                  title="No throughput data yet"
                  description="Start scraping assets to see pipeline throughput over time"
                  size="sm"
                />
              )}
            </div>
          </CardContent>
        </Card>

        {/* Industry Distribution */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-brand-500" />
              Industry Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              {industryLoading ? (
                <div className="h-full flex items-center justify-center">
                  <div className="animate-pulse text-surface-500">Loading...</div>
                </div>
              ) : hasPieData ? (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#27272a',
                        border: '1px solid #3f3f46',
                        borderRadius: '8px'
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState
                  icon={PieChartIcon}
                  title="No industry data yet"
                  description="Assets will be categorized by industry as they're processed"
                  size="sm"
                />
              )}
            </div>
            {/* Legend */}
            {hasPieData && (
              <div className="grid grid-cols-2 gap-2 mt-4">
                {pieData.slice(0, 6).map((item) => (
                  <div key={item.name} className="flex items-center gap-2 text-xs">
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: item.color }}
                    />
                    <span className="text-surface-400 truncate">{item.name}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Queue Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-brand-500" />
              Queue Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            {metricsLoading ? (
              <div className="py-8 text-center text-surface-500 animate-pulse">
                Loading queue status...
              </div>
            ) : hasQueueData ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">Pending Jobs</span>
                  <span className="text-xl font-semibold text-white">
                    {formatNumber(metrics?.queue?.pending_jobs ?? 0)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">In Progress</span>
                  <span className="text-xl font-semibold text-brand-400">
                    {formatNumber(metrics?.queue?.in_progress_jobs ?? 0)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">Completed Today</span>
                  <span className="text-xl font-semibold text-success-500">
                    {formatNumber(metrics?.queue?.completed_jobs ?? 0)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">Failed</span>
                  <span className="text-xl font-semibold text-danger-500">
                    {formatNumber(metrics?.queue?.failed_jobs ?? 0)}
                  </span>
                </div>
                <div className="pt-4 border-t border-surface-800">
                  <div className="flex items-center justify-between">
                    <span className="text-surface-400">Avg Processing Time</span>
                    <span className="text-white font-medium">
                      {formatDuration(metrics?.queue?.avg_processing_time_seconds ?? 0)}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">Pending Jobs</span>
                  <span className="text-xl font-semibold text-surface-600">0</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">In Progress</span>
                  <span className="text-xl font-semibold text-surface-600">0</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">Completed Today</span>
                  <span className="text-xl font-semibold text-surface-600">0</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-surface-400">Failed</span>
                  <span className="text-xl font-semibold text-surface-600">0</span>
                </div>
                <div className="pt-4 border-t border-surface-800">
                  <p className="text-xs text-surface-500 text-center">
                    No jobs have been processed yet
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Jobs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="w-5 h-5 text-brand-500" />
              Recent Jobs
            </CardTitle>
          </CardHeader>
          <CardContent>
            {jobsLoading ? (
              <div className="py-8 text-center text-surface-500 animate-pulse">
                Loading recent jobs...
              </div>
            ) : hasJobs ? (
              <div className="space-y-3">
                {recentJobs?.jobs.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center justify-between p-3 rounded-lg bg-surface-800/50"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-white truncate">
                          {job.job_type.replace(/_/g, ' ')}
                        </p>
                        <StatusBadge status={job.status} />
                      </div>
                      <p className="text-xs text-surface-500 mt-1">
                        {job.source?.replace(/_/g, ' ') || 'System'} •{' '}
                        {formatRelativeTime(job.created_at)}
                      </p>
                    </div>
                    {job.assets_processed > 0 && (
                      <span className="text-sm text-surface-400">
                        {job.assets_processed} assets
                      </span>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={ListTodo}
                title="No jobs yet"
                description="Jobs will appear here when you start scraping or processing assets"
                size="sm"
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
