"""
Jobs API Router

Endpoints for job queue management and control.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends

from ..models import (
    Job, JobCreate, JobStatus, JobType, JobListResponse,
    JobControlRequest, JobControlResponse, ScraperSource
)
from ..services.firestore_service import FirestoreService, get_firestore_service
from ..services.job_service import JobService, get_job_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[JobStatus] = None,
    job_type: Optional[JobType] = None,
    source: Optional[ScraperSource] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """List all jobs with optional filters."""
    jobs, total = await firestore.get_jobs(
        status=status,
        job_type=job_type,
        source=source,
        page=page,
        page_size=page_size
    )
    
    return JobListResponse(
        jobs=jobs,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total
    )


@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: str,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Get a specific job by ID."""
    job = await firestore.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("", response_model=Job)
async def create_job(
    job_create: JobCreate,
    job_service: JobService = Depends(get_job_service)
):
    """Create a new job."""
    return await job_service.create_job(job_create)


@router.post("/control", response_model=JobControlResponse)
async def control_jobs(
    request: JobControlRequest,
    job_service: JobService = Depends(get_job_service)
):
    """
    Control multiple jobs.
    
    Actions:
    - start: Start pending jobs
    - stop: Stop running jobs
    - pause: Pause running jobs
    - resume: Resume paused jobs
    - retry: Retry failed jobs
    - cancel: Cancel any jobs
    """
    return await job_service.control_jobs(request)


@router.post("/{job_id}/retry", response_model=Job)
async def retry_job(
    job_id: str,
    firestore: FirestoreService = Depends(get_firestore_service),
    job_service: JobService = Depends(get_job_service)
):
    """Retry a failed job."""
    job = await firestore.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=400, 
            detail=f"Can only retry failed jobs, current status: {job.status}"
        )
    
    result = await job_service.control_jobs(
        JobControlRequest(action="retry", job_ids=[job_id])
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail="Failed to retry job")
    
    return await firestore.get_job(job_id)


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    firestore: FirestoreService = Depends(get_firestore_service),
    job_service: JobService = Depends(get_job_service)
):
    """Cancel a job."""
    job = await firestore.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    await job_service.control_jobs(
        JobControlRequest(action="cancel", job_ids=[job_id])
    )
    
    return {"message": f"Job {job_id} cancelled"}


@router.post("/retry-all-failed")
async def retry_all_failed_jobs(
    max_jobs: int = Query(default=10, ge=1, le=100),
    job_service: JobService = Depends(get_job_service)
):
    """Retry all failed jobs up to a limit."""
    retried = await job_service.retry_failed_jobs(max_jobs)
    return {"message": f"Retried {retried} failed jobs"}


@router.get("/stats/by-status")
async def get_job_stats_by_status(
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Get job counts grouped by status."""
    return await firestore.get_job_counts_by_status()

