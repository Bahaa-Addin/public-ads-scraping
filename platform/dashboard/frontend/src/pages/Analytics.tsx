import { useState } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { BarChart3 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Select } from '@/components/ui/Select';
import { EmptyState } from '@/components/ui/EmptyState';
import {
  useIndustryDistribution,
  useMultiTimeSeries,
  useQualityDistribution,
  useCtaDistribution,
  useDashboardMetrics
} from '@/lib/useDataHooks';
import { useIsTemplateMode } from '@/lib/useTemplateMode';
import { INDUSTRY_COLORS, formatIndustryName, formatNumber } from '@/lib/utils';
import { format, parseISO } from 'date-fns';

const CHART_COLORS = ['#0ea5e9', '#8b5cf6', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4'];

export default function Analytics() {
  const isTemplate = useIsTemplateMode();
  const [timeRange, setTimeRange] = useState('24');

  const { data: metrics } = useDashboardMetrics();
  const { data: industryData, isLoading: industryLoading } = useIndustryDistribution();

  const { data: timeSeriesData, isLoading: timeSeriesLoading } = useMultiTimeSeries(
    ['assets_scraped', 'features_extracted', 'prompts_generated'],
    parseInt(timeRange)
  );

  const { data: qualityData, isLoading: qualityLoading } = useQualityDistribution();
  const { data: ctaData, isLoading: ctaLoading } = useCtaDistribution();

  // Format industry data for pie chart
  const pieData =
    industryData?.slice(0, 8).map((item) => ({
      name: formatIndustryName(item.industry),
      value: item.count,
      color: INDUSTRY_COLORS[item.industry] || '#6b7280'
    })) || [];

  // Format time series data for line chart
  const lineChartData =
    timeSeriesData?.[0]?.data.map((_, index) => {
      const point: Record<string, number | string> = {
        time: format(parseISO(timeSeriesData[0].data[index].timestamp), 'HH:mm')
      };
      timeSeriesData.forEach((series) => {
        point[series.name] = series.data[index]?.value || 0;
      });
      return point;
    }) || [];

  // Format quality data for bar chart
  const qualityChartData = qualityData
    ? Object.entries(qualityData).map(([range, count]) => ({
        range,
        count: count as number
      }))
    : [];

  // Format CTA data for bar chart
  const ctaChartData = ctaData
    ? Object.entries(ctaData)
        .sort((a, b) => (b[1] as number) - (a[1] as number))
        .slice(0, 8)
        .map(([type, count]) => ({
          type: type.replace(/_/g, ' '),
          count: count as number
        }))
    : [];

  // Source distribution for bar chart
  const sourceData = metrics?.pipeline.by_source
    ? Object.entries(metrics.pipeline.by_source).map(([source, count]) => ({
        source: source.replace(/_/g, ' '),
        count
      }))
    : [];

  // Check if we have data
  const hasLineData = lineChartData.length > 0;
  const hasPieData = pieData.length > 0 && pieData.some((d) => d.value > 0);
  const hasSourceData = sourceData.length > 0 && sourceData.some((d) => d.count > 0);
  const hasQualityData =
    qualityChartData.length > 0 && qualityChartData.some((d) => (d.count as number) > 0);
  const hasCtaData = ctaChartData.length > 0 && ctaChartData.some((d) => (d.count as number) > 0);
  const hasIndustryData =
    industryData && industryData.length > 0 && industryData.some((d) => d.count > 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-surface-400 mt-1">
            {isTemplate
              ? 'Preview analytics with sample data'
              : 'Deep insights into your agentic ads pipeline'}
          </p>
        </div>
        <Select
          options={[
            { value: '6', label: 'Last 6 hours' },
            { value: '24', label: 'Last 24 hours' },
            { value: '72', label: 'Last 3 days' },
            { value: '168', label: 'Last 7 days' }
          ]}
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="w-40"
        />
      </div>

      {/* Pipeline Throughput */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Throughput Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[350px]">
            {timeSeriesLoading ? (
              <div className="h-full flex items-center justify-center">
                <div className="animate-pulse text-surface-500">Loading chart...</div>
              </div>
            ) : hasLineData ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={lineChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                  <XAxis dataKey="time" stroke="#71717a" fontSize={12} />
                  <YAxis stroke="#71717a" fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#27272a',
                      border: '1px solid #3f3f46',
                      borderRadius: '8px'
                    }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="assets_scraped"
                    name="Assets Scraped"
                    stroke="#0ea5e9"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="features_extracted"
                    name="Features Extracted"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="prompts_generated"
                    name="Prompts Generated"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                icon={BarChart3}
                title="No throughput data yet"
                description="Start processing assets to see pipeline analytics"
                size="sm"
              />
            )}
          </div>
        </CardContent>
      </Card>

      {/* Distribution Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Industry Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Industry Distribution</CardTitle>
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
                      label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                      labelLine={false}
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
                      formatter={(value: number) => formatNumber(value)}
                    />
                  </PieChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState
                  icon={BarChart3}
                  title="No industry data yet"
                  description="Assets will be categorized by industry as they're processed"
                  size="sm"
                />
              )}
            </div>
          </CardContent>
        </Card>

        {/* Source Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Assets by Source</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              {hasSourceData ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={sourceData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis type="number" stroke="#71717a" fontSize={12} />
                    <YAxis
                      type="category"
                      dataKey="source"
                      stroke="#71717a"
                      fontSize={12}
                      width={120}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#27272a',
                        border: '1px solid #3f3f46',
                        borderRadius: '8px'
                      }}
                    />
                    <Bar dataKey="count" fill="#0ea5e9" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState
                  icon={BarChart3}
                  title="No source data yet"
                  description="Start scraping from different sources to see distribution"
                  size="sm"
                />
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quality Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Quality Score Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              {qualityLoading ? (
                <div className="h-full flex items-center justify-center">
                  <div className="animate-pulse text-surface-500">Loading...</div>
                </div>
              ) : hasQualityData ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={qualityChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis dataKey="range" stroke="#71717a" fontSize={12} />
                    <YAxis stroke="#71717a" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#27272a',
                        border: '1px solid #3f3f46',
                        borderRadius: '8px'
                      }}
                    />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {qualityChartData.map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={CHART_COLORS[index % CHART_COLORS.length]}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState
                  icon={BarChart3}
                  title="No quality data yet"
                  description="Quality scores will appear as features are extracted"
                  size="sm"
                />
              )}
            </div>
          </CardContent>
        </Card>

        {/* CTA Types */}
        <Card>
          <CardHeader>
            <CardTitle>CTA Type Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              {ctaLoading ? (
                <div className="h-full flex items-center justify-center">
                  <div className="animate-pulse text-surface-500">Loading...</div>
                </div>
              ) : hasCtaData ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={ctaChartData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                    <XAxis type="number" stroke="#71717a" fontSize={12} />
                    <YAxis
                      type="category"
                      dataKey="type"
                      stroke="#71717a"
                      fontSize={12}
                      width={100}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#27272a',
                        border: '1px solid #3f3f46',
                        borderRadius: '8px'
                      }}
                    />
                    <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState
                  icon={BarChart3}
                  title="No CTA data yet"
                  description="CTA types will appear as features are extracted"
                  size="sm"
                />
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Industry Breakdown Table */}
      <Card>
        <CardHeader>
          <CardTitle>Industry Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          {industryLoading ? (
            <div className="py-8 text-center text-surface-500 animate-pulse">
              Loading industry data...
            </div>
          ) : hasIndustryData ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-surface-800">
                    <th className="text-left text-xs font-semibold text-surface-400 uppercase tracking-wider py-3">
                      Industry
                    </th>
                    <th className="text-right text-xs font-semibold text-surface-400 uppercase tracking-wider py-3">
                      Count
                    </th>
                    <th className="text-right text-xs font-semibold text-surface-400 uppercase tracking-wider py-3">
                      Percentage
                    </th>
                    <th className="text-left text-xs font-semibold text-surface-400 uppercase tracking-wider py-3 pl-4">
                      Distribution
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {industryData?.map((item) => (
                    <tr key={item.industry} className="border-b border-surface-800/50">
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <span
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: INDUSTRY_COLORS[item.industry] || '#6b7280' }}
                          />
                          <span className="text-white">{formatIndustryName(item.industry)}</span>
                        </div>
                      </td>
                      <td className="text-right text-white font-medium py-3">
                        {formatNumber(item.count)}
                      </td>
                      <td className="text-right text-surface-400 py-3">
                        {item.percentage.toFixed(1)}%
                      </td>
                      <td className="py-3 pl-4">
                        <div className="w-full max-w-[200px] h-2 bg-surface-800 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${item.percentage}%`,
                              backgroundColor: INDUSTRY_COLORS[item.industry] || '#6b7280'
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={BarChart3}
              title="No industry data yet"
              description="Industry breakdown will appear as assets are processed"
              size="sm"
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
