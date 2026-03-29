"""
Jobs API Router

Endpoints for job queue management, control, and action triggers.
"""

import httpx
import json
import logging
from pathlib import Path
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..config import get_settings
from ..models import (
    Job, JobCreate, JobStatus, JobType, JobListResponse,
    JobControlRequest, JobControlResponse, ScraperSource
)
from ..services.firestore_service import FirestoreService, get_firestore_service
from ..services.job_service import JobService, get_job_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ==========================================================================
# Request Models for Job Actions
# ==========================================================================

class ScrapeJobRequest(BaseModel):
    """Request to start a scraping job."""
    sources: List[str] = Field(default=["meta_ad_library"], description="Sources to scrape from")
    query: Optional[str] = Field(default=None, description="Search query for scraping")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum items to scrape")


class ExtractJobRequest(BaseModel):
    """Request to start a feature extraction job."""
    asset_ids: Optional[List[str]] = Field(default=None, description="Specific asset IDs to process, or all if empty")
    reprocess: bool = Field(default=False, description="Reprocess assets that already have features")


class GenerateJobRequest(BaseModel):
    """Request to start a prompt generation job."""
    asset_ids: Optional[List[str]] = Field(default=None, description="Specific asset IDs to process, or all if empty")
    regenerate: bool = Field(default=False, description="Regenerate prompts that already exist")


class ClassifyJobRequest(BaseModel):
    """Request to start an industry classification job."""
    asset_ids: Optional[List[str]] = Field(default=None, description="Specific asset IDs to process, or all if empty")
    reclassify: bool = Field(default=False, description="Reclassify assets that already have industry")


class PipelineJobRequest(BaseModel):
    """Request to run the full pipeline."""
    sources: List[str] = Field(default=["meta_ad_library"], description="Sources to scrape from")
    query: Optional[str] = Field(default=None, description="Search query for scraping")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum items to scrape")
    skip_steps: List[str] = Field(default=[], description="Steps to skip: scrape, extract, generate, classify")


class JobActionResponse(BaseModel):
    """Response from a job action."""
    job_id: str
    job_type: str
    status: str
    message: str


# ==========================================================================
# Job Action Helper
# ==========================================================================

async def _trigger_agent_job(job_type: str, payload: dict, firestore: FirestoreService) -> str:
    """Create a job and trigger the agent to process it."""
    settings = get_settings()
    
    # Create the job in local storage
    job_data = {
        "job_type": job_type,
        "payload": payload,
        "status": JobStatus.PENDING.value,
        "assets_processed": 0,
        "retry_count": 0,
    }
    
    job_id = await firestore.create_job(job_data)
    
    # Try to trigger the agent service (non-blocking)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.agent_api_url}/api/v1/jobs/trigger",
                json={"job_id": job_id, "job_type": job_type, "payload": payload}
            )
            logger.info(f"Triggered agent for job {job_id}")
    except Exception as e:
        logger.warning(f"Could not trigger agent service: {e}")
        # Job is still created, agent can pick it up later
    
    return job_id


# ==========================================================================
# Job Action Endpoints
# ==========================================================================

@router.post("/scrape", response_model=JobActionResponse)
async def start_scrape_job(
    request: ScrapeJobRequest,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """
    Start a scraping job to collect ads from specified sources.
    
    The job will be queued and processed by the agent service.
    """
    job_id = await _trigger_agent_job(
        JobType.SCRAPE.value,
        {
            "sources": request.sources,
            "query": request.query,
            "limit": request.limit
        },
        firestore
    )
    
    return JobActionResponse(
        job_id=job_id,
        job_type=JobType.SCRAPE.value,
        status="pending",
        message=f"Scraping job created for {len(request.sources)} source(s)"
    )


@router.post("/extract", response_model=JobActionResponse)
async def start_extract_job(
    request: ExtractJobRequest,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """
    Start a feature extraction job.
    
    Extracts visual features from scraped assets.
    """
    job_id = await _trigger_agent_job(
        JobType.EXTRACT_FEATURES.value,
        {
            "asset_ids": request.asset_ids,
            "reprocess": request.reprocess
        },
        firestore
    )
    
    return JobActionResponse(
        job_id=job_id,
        job_type=JobType.EXTRACT_FEATURES.value,
        status="pending",
        message="Feature extraction job created"
    )


@router.post("/generate", response_model=JobActionResponse)
async def start_generate_job(
    request: GenerateJobRequest,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """
    Start a prompt generation job.
    
    Generates reverse prompts from extracted features.
    """
    job_id = await _trigger_agent_job(
        JobType.GENERATE_PROMPT.value,
        {
            "asset_ids": request.asset_ids,
            "regenerate": request.regenerate
        },
        firestore
    )
    
    return JobActionResponse(
        job_id=job_id,
        job_type=JobType.GENERATE_PROMPT.value,
        status="pending",
        message="Prompt generation job created"
    )


@router.post("/classify", response_model=JobActionResponse)
async def start_classify_job(
    request: ClassifyJobRequest,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """
    Start an industry classification job.
    
    Classifies assets into industry categories.
    """
    job_id = await _trigger_agent_job(
        JobType.CLASSIFY.value,
        {
            "asset_ids": request.asset_ids,
            "reclassify": request.reclassify
        },
        firestore
    )
    
    return JobActionResponse(
        job_id=job_id,
        job_type=JobType.CLASSIFY.value,
        status="pending",
        message="Classification job created"
    )


@router.post("/pipeline", response_model=JobActionResponse)
async def start_pipeline_job(
    request: PipelineJobRequest,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """
    Start a full pipeline job.
    
    Runs: scrape → extract features → generate prompts → classify
    Each step can be optionally skipped.
    """
    job_id = await _trigger_agent_job(
        JobType.FULL_PIPELINE.value,
        {
            "sources": request.sources,
            "query": request.query,
            "limit": request.limit,
            "skip_steps": request.skip_steps
        },
        firestore
    )
    
    steps = ["scrape", "extract", "generate", "classify"]
    active_steps = [s for s in steps if s not in request.skip_steps]
    
    return JobActionResponse(
        job_id=job_id,
        job_type=JobType.FULL_PIPELINE.value,
        status="pending",
        message=f"Full pipeline started: {' → '.join(active_steps)}"
    )


@router.post("/{job_id}/cancel", response_model=JobActionResponse)
async def cancel_job_by_id(
    job_id: str,
    firestore: FirestoreService = Depends(get_firestore_service),
    job_service: JobService = Depends(get_job_service)
):
    """Cancel a running or pending job."""
    job = await firestore.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in [JobStatus.PENDING, JobStatus.IN_PROGRESS]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status}"
        )
    
    await firestore.update_job(job_id, {"status": JobStatus.CANCELLED.value})
    
    return JobActionResponse(
        job_id=job_id,
        job_type=job.job_type.value if job.job_type else "unknown",
        status="cancelled",
        message="Job cancelled successfully"
    )


@router.get("/{job_id}/status")
async def get_job_status(
    job_id: str,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Get detailed status of a job."""
    job = await firestore.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "status": job.status.value if job.status else "unknown",
        "job_type": job.job_type.value if job.job_type else "unknown",
        "assets_processed": job.assets_processed or 0,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "error_message": job.error_message
    }


# ==========================================================================
# Existing Endpoints
# ==========================================================================


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


# ==========================================================================
# Screenshot Endpoints (for job replay) - MUST be before /{job_id} routes
# ==========================================================================

def _get_screenshots_path() -> Path:
    """Get the screenshots directory path."""
    settings = get_settings()
    return Path(settings.data_dir) / "screenshots"


@router.get("/with-screenshots", tags=["Screenshots"])
async def get_jobs_with_screenshots():
    """Get list of job IDs that have screenshots available."""
    screenshots_path = _get_screenshots_path()
    
    if not screenshots_path.exists():
        return {"jobs": [], "count": 0}
    
    jobs = []
    for job_dir in screenshots_path.iterdir():
        if job_dir.is_dir() and any(job_dir.glob("*.jpg")):
            jobs.append(job_dir.name)
    
    return {"jobs": sorted(jobs), "count": len(jobs)}


@router.get("/{job_id}/screenshots", tags=["Screenshots"])
async def get_job_screenshots(job_id: str):
    """Get list of screenshots for a job."""
    screenshots_path = _get_screenshots_path() / job_id
    
    if not screenshots_path.exists():
        return {"job_id": job_id, "count": 0, "screenshots": []}
    
    screenshots = []
    for img_path in sorted(screenshots_path.glob("*.jpg")):
        meta_path = img_path.parent / f"{img_path.name}.json"
        
        meta: Dict[str, Any] = {}
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
            except json.JSONDecodeError:
                pass
        
        screenshots.append({
            "filename": img_path.name,
            "url": f"/api/v1/screenshots/{job_id}/{img_path.name}",
            "timestamp": meta.get("timestamp"),
            "page_url": meta.get("url"),
            "action": meta.get("action"),
            "step": meta.get("step"),
        })
    
    return {"job_id": job_id, "count": len(screenshots), "screenshots": screenshots}


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
