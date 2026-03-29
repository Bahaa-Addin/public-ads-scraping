import { useState, useRef, useEffect } from 'react';
import {
  RefreshCw,
  XCircle,
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  ListTodo,
  Film,
  X,
  FileText,
  Copy
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { SearchInput } from '@/components/ui/Input';
import { StatusBadge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { JobReplayPlayer } from '@/components/JobReplayPlayer';
import {
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableHeader,
  TableCell,
  TableLoading
} from '@/components/ui/Table';
import { useJobs, useJobStats, useControlJobs, useRetryAllFailedJobs } from '@/lib/useDataHooks';
import { useJobsWithScreenshots } from '@/hooks/useJobScreenshots';
import { useIsTemplateMode } from '@/lib/useTemplateMode';
import { useNavigate } from 'react-router-dom';
import { formatRelativeTime, formatSourceName, cn } from '@/lib/utils';

const statusOptions = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'retrying', label: 'Retrying' },
  { value: 'cancelled', label: 'Cancelled' }
];

const typeOptions = [
  { value: '', label: 'All Types' },
  { value: 'scrape', label: 'Scrape' },
  { value: 'extract_features', label: 'Extract Features' },
  { value: 'generate_prompt', label: 'Generate Prompt' },
  { value: 'classify_industry', label: 'Classify Industry' }
];

export default function Jobs() {
  const isTemplate = useIsTemplateMode();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [selectedJobs, setSelectedJobs] = useState<string[]>([]);
  const [replayJobId, setReplayJobId] = useState<string | null>(null);
  const [actionMenuJobId, setActionMenuJobId] = useState<string | null>(null);
  const actionMenuRef = useRef<HTMLDivElement>(null);
  const [filters, setFilters] = useState({
    status: '',
    job_type: '',
    source: ''
  });

  // Close action menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (actionMenuRef.current && !actionMenuRef.current.contains(event.target as Node)) {
        setActionMenuJobId(null);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch jobs that have screenshots for replay
  const { data: jobsWithScreenshots } = useJobsWithScreenshots();
  const hasScreenshots = (jobId: string) => jobsWithScreenshots?.jobs.includes(jobId) ?? false;

  const { data: jobs, isLoading } = useJobs({
    page,
    page_size: 15,
    status: filters.status || undefined,
    job_type: filters.job_type || undefined,
    source: filters.source || undefined
  });

  const { data: stats } = useJobStats();

  const controlMutation = useControlJobs();
  const retryAllMutation = useRetryAllFailedJobs();

  const handleSelectAll = () => {
    if (selectedJobs.length === jobs?.jobs.length) {
      setSelectedJobs([]);
    } else {
      setSelectedJobs(jobs?.jobs.map((j) => j.id) || []);
    }
  };

  const handleSelectJob = (jobId: string) => {
    setSelectedJobs((prev) =>
      prev.includes(jobId) ? prev.filter((id) => id !== jobId) : [...prev, jobId]
    );
  };

  const handleControl = (action: string) => {
    if (selectedJobs.length > 0) {
      controlMutation.mutate({ action, jobIds: selectedJobs });
      setSelectedJobs([]);
    }
  };

  const handleJobAction = (action: string, jobId: string) => {
    setActionMenuJobId(null);
    switch (action) {
      case 'retry':
        controlMutation.mutate({ action: 'retry', jobIds: [jobId] });
        break;
      case 'cancel':
        controlMutation.mutate({ action: 'cancel', jobIds: [jobId] });
        break;
      case 'replay':
        setReplayJobId(jobId);
        break;
      case 'logs':
        // Navigate to logs filtered by this job
        navigate(`/logs?job_id=${jobId}`);
        break;
      case 'copy':
        navigator.clipboard.writeText(jobId);
        break;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Job Queue</h1>
          <p className="text-surface-400 mt-1">
            {isTemplate
              ? 'Preview job management with sample data'
              : 'Manage and monitor pipeline jobs'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={() => retryAllMutation.mutate(10)}
            loading={retryAllMutation.isPending}
            disabled={(stats?.failed || 0) === 0}
          >
            <RefreshCw className="w-4 h-4" />
            Retry Failed ({stats?.failed || 0})
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-4">
        {[
          { label: 'Pending', value: stats?.pending || 0, color: 'text-yellow-500' },
          { label: 'In Progress', value: stats?.in_progress || 0, color: 'text-blue-500' },
          { label: 'Completed', value: stats?.completed || 0, color: 'text-green-500' },
          { label: 'Failed', value: stats?.failed || 0, color: 'text-red-500' },
          { label: 'Retrying', value: stats?.retrying || 0, color: 'text-orange-500' },
          { label: 'Cancelled', value: stats?.cancelled || 0, color: 'text-gray-500' }
        ].map((stat) => (
          <div key={stat.label} className="card p-4">
            <p className="text-xs text-surface-400">{stat.label}</p>
            <p className={cn('text-2xl font-bold mt-1', stat.color)}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Filters and Actions */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-4">
              <Select
                options={statusOptions}
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                placeholder="Filter by status"
              />
              <Select
                options={typeOptions}
                value={filters.job_type}
                onChange={(e) => setFilters({ ...filters, job_type: e.target.value })}
                placeholder="Filter by type"
              />
              <SearchInput placeholder="Search jobs..." className="w-full" />
            </div>

            {selectedJobs.length > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-surface-400">{selectedJobs.length} selected</span>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => handleControl('retry')}
                  loading={controlMutation.isPending}
                >
                  <RefreshCw className="w-4 h-4" />
                  Retry
                </Button>
                <Button
                  size="sm"
                  variant="danger"
                  onClick={() => handleControl('cancel')}
                  loading={controlMutation.isPending}
                >
                  <XCircle className="w-4 h-4" />
                  Cancel
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Jobs Table */}
      <Card>
        <Table>
          <TableHead>
            <TableRow>
              <TableHeader className="w-12">
                <input
                  type="checkbox"
                  checked={selectedJobs.length === jobs?.jobs.length && jobs?.jobs.length > 0}
                  onChange={handleSelectAll}
                  className="rounded border-surface-600 bg-surface-800 text-brand-500 focus:ring-brand-500"
                />
              </TableHeader>
              <TableHeader>Job ID</TableHeader>
              <TableHeader>Type</TableHeader>
              <TableHeader>Source</TableHeader>
              <TableHeader>Status</TableHeader>
              <TableHeader>Assets</TableHeader>
              <TableHeader>Created</TableHeader>
              <TableHeader className="w-12">Actions</TableHeader>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              <TableLoading rows={5} cols={8} />
            ) : !jobs?.jobs || jobs.jobs.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12">
                  <EmptyState
                    icon={ListTodo}
                    title={filters.status || filters.job_type ? 'No matching jobs' : 'No jobs yet'}
                    description={
                      filters.status || filters.job_type
                        ? 'Try adjusting your filters to find jobs'
                        : 'Jobs will appear here when you start scraping assets or processing data'
                    }
                    size="sm"
                  />
                </td>
              </tr>
            ) : (
              jobs?.jobs.map((job) => (
                <TableRow key={job.id} selected={selectedJobs.includes(job.id)}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selectedJobs.includes(job.id)}
                      onChange={() => handleSelectJob(job.id)}
                      className="rounded border-surface-600 bg-surface-800 text-brand-500 focus:ring-brand-500"
                    />
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-xs text-surface-400">
                      {job.id.slice(0, 8)}...
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="capitalize">{job.job_type.replace(/_/g, ' ')}</span>
                  </TableCell>
                  <TableCell>{job.source ? formatSourceName(job.source) : '-'}</TableCell>
                  <TableCell>
                    <StatusBadge status={job.status} />
                  </TableCell>
                  <TableCell>{job.assets_processed > 0 ? job.assets_processed : '-'}</TableCell>
                  <TableCell className="text-surface-400">
                    {formatRelativeTime(job.created_at)}
                  </TableCell>
                  <TableCell>
                    <div className="relative flex items-center gap-1">
                      {hasScreenshots(job.id) && (
                        <button
                          onClick={() => setReplayJobId(job.id)}
                          className="p-1 text-brand-400 hover:text-brand-300 transition-colors"
                          title="View Replay"
                        >
                          <Film className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() =>
                          setActionMenuJobId(actionMenuJobId === job.id ? null : job.id)
                        }
                        className="p-1 text-surface-400 hover:text-white transition-colors"
                      >
                        <MoreVertical className="w-4 h-4" />
                      </button>

                      {/* Action Dropdown Menu */}
                      {actionMenuJobId === job.id && (
                        <div
                          ref={actionMenuRef}
                          className="absolute right-0 top-8 z-50 w-40 py-1 bg-surface-800 border border-surface-700 rounded-lg shadow-xl"
                        >
                          <button
                            onClick={() => handleJobAction('copy', job.id)}
                            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-surface-300 hover:bg-surface-700 hover:text-white"
                          >
                            <Copy className="w-4 h-4" />
                            Copy ID
                          </button>
                          <button
                            onClick={() => handleJobAction('logs', job.id)}
                            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-surface-300 hover:bg-surface-700 hover:text-white"
                          >
                            <FileText className="w-4 h-4" />
                            View Logs
                          </button>
                          {hasScreenshots(job.id) && (
                            <button
                              onClick={() => handleJobAction('replay', job.id)}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-surface-300 hover:bg-surface-700 hover:text-white"
                            >
                              <Film className="w-4 h-4" />
                              View Replay
                            </button>
                          )}
                          {job.status === 'failed' && (
                            <button
                              onClick={() => handleJobAction('retry', job.id)}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-surface-300 hover:bg-surface-700 hover:text-white"
                            >
                              <RefreshCw className="w-4 h-4" />
                              Retry Job
                            </button>
                          )}
                          {(job.status === 'pending' || job.status === 'in_progress') && (
                            <button
                              onClick={() => handleJobAction('cancel', job.id)}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-surface-700 hover:text-red-300"
                            >
                              <XCircle className="w-4 h-4" />
                              Cancel Job
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        {jobs && jobs.total > 15 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-surface-800">
            <span className="text-sm text-surface-400">
              Showing {(page - 1) * 15 + 1} to {Math.min(page * 15, jobs.total)} of {jobs.total}
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
                disabled={!jobs.has_more}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Replay Modal */}
      {replayJobId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80">
          <div className="relative w-full max-w-5xl mx-4">
            <button
              onClick={() => setReplayJobId(null)}
              className="absolute -top-12 right-0 p-2 text-white hover:text-surface-300 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
            <JobReplayPlayer jobId={replayJobId} onClose={() => setReplayJobId(null)} />
          </div>
        </div>
      )}
    </div>
  );
}
