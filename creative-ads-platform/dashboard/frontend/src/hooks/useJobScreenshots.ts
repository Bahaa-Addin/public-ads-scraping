/**
 * useJobScreenshots - Hook for fetching job replay screenshots
 * 
 * Provides access to stored screenshots for job replay functionality.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

// Default to agent API port
const AGENT_API_URL = import.meta.env.VITE_AGENT_API_URL || 'http://localhost:8080'

export interface Screenshot {
  filename: string
  url: string
  timestamp: string | null
  page_url: string | null
  action: string | null
  step: number | null
}

interface JobScreenshotsResponse {
  job_id: string
  count: number
  screenshots: Screenshot[]
}

interface JobsWithScreenshotsResponse {
  jobs: string[]
  count: number
}

interface StorageResponse {
  bytes: number
  mb: number
}

/**
 * Fetch screenshots for a specific job
 */
async function fetchJobScreenshots(jobId: string): Promise<JobScreenshotsResponse> {
  const response = await fetch(`${AGENT_API_URL}/api/v1/jobs/${jobId}/screenshots`)
  if (!response.ok) {
    throw new Error(`Failed to fetch screenshots for job ${jobId}`)
  }
  return response.json()
}

/**
 * Fetch list of jobs that have screenshots
 */
async function fetchJobsWithScreenshots(): Promise<JobsWithScreenshotsResponse> {
  const response = await fetch(`${AGENT_API_URL}/api/v1/jobs/with-screenshots`)
  if (!response.ok) {
    throw new Error('Failed to fetch jobs with screenshots')
  }
  return response.json()
}

/**
 * Fetch screenshot storage usage
 */
async function fetchStorageUsage(): Promise<StorageResponse> {
  const response = await fetch(`${AGENT_API_URL}/api/v1/screenshots/storage`)
  if (!response.ok) {
    throw new Error('Failed to fetch storage usage')
  }
  return response.json()
}

/**
 * Delete screenshots for a job
 */
async function deleteJobScreenshots(jobId: string): Promise<void> {
  const response = await fetch(`${AGENT_API_URL}/api/v1/jobs/${jobId}/screenshots`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    throw new Error(`Failed to delete screenshots for job ${jobId}`)
  }
}

/**
 * Hook to get screenshots for a specific job
 */
export function useJobScreenshots(jobId: string | null) {
  return useQuery({
    queryKey: ['jobScreenshots', jobId],
    queryFn: () => fetchJobScreenshots(jobId!),
    enabled: !!jobId,
    staleTime: 30000, // Screenshots don't change, cache for 30s
  })
}

/**
 * Hook to get list of jobs that have screenshots
 */
export function useJobsWithScreenshots() {
  return useQuery({
    queryKey: ['jobsWithScreenshots'],
    queryFn: fetchJobsWithScreenshots,
    staleTime: 10000, // Refresh every 10s
  })
}

/**
 * Hook to get screenshot storage usage
 */
export function useScreenshotStorage() {
  return useQuery({
    queryKey: ['screenshotStorage'],
    queryFn: fetchStorageUsage,
    staleTime: 30000,
  })
}

/**
 * Hook to delete screenshots for a job
 */
export function useDeleteJobScreenshots() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: deleteJobScreenshots,
    onSuccess: (_, jobId) => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['jobScreenshots', jobId] })
      queryClient.invalidateQueries({ queryKey: ['jobsWithScreenshots'] })
      queryClient.invalidateQueries({ queryKey: ['screenshotStorage'] })
    },
  })
}

/**
 * Build full URL for a screenshot
 */
export function getScreenshotUrl(jobId: string, filename: string): string {
  return `${AGENT_API_URL}/api/v1/screenshots/${jobId}/${filename}`
}

/**
 * Check if a job has screenshots available
 */
export function useJobHasScreenshots(jobId: string | null) {
  const { data } = useJobsWithScreenshots()
  
  if (!jobId || !data) return false
  return data.jobs.includes(jobId)
}
