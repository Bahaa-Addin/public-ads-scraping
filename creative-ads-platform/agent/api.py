"""
Agent API - FastAPI HTTP Interface

Provides HTTP endpoints for the Agent Brain:
- Health checks
- Job triggering
- Status monitoring
- Metrics retrieval
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent_brain import AgentBrain, ScrapingTask, PipelineStage
from .config import Config, ScraperSource, IndustryCategory
from .orchestrator import Orchestrator

logger = logging.getLogger(__name__)

# Global instances
orchestrator: Optional[Orchestrator] = None


# =============================================================================
# Request/Response Models
# =============================================================================

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    uptime_seconds: float
    version: str = "1.0.0"


class TriggerScrapingRequest(BaseModel):
    sources: Optional[List[str]] = None
    industries: Optional[List[str]] = None
    max_items_per_source: int = Field(default=100, ge=1, le=1000)
    priority: int = Field(default=0, ge=0, le=10)


class TriggerScrapingResponse(BaseModel):
    triggered: bool
    job_ids: List[str]
    sources: List[str]
    message: str


class ScrapingJobRequest(BaseModel):
    source: str
    query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    max_items: int = Field(default=100, ge=1, le=1000)


class ScrapingJobResponse(BaseModel):
    job_id: str
    status: str
    message: str


class PipelineStatusResponse(BaseModel):
    running: bool
    active_tasks: int
    metrics: Dict[str, int]
    queue: Dict[str, int]
    last_updated: str


class MetricsResponse(BaseModel):
    assets_scraped: int
    features_extracted: int
    prompts_generated: int
    assets_stored: int
    errors: int
    by_source: Dict[str, int]
    by_industry: Dict[str, int]


class JobTriggerRequest(BaseModel):
    """Request from dashboard to trigger a job."""
    job_id: str
    job_type: str
    payload: Dict[str, Any]


class JobTriggerResponse(BaseModel):
    """Response for job trigger."""
    status: str
    message: str
    job_id: str


# =============================================================================
# Lifespan Management
# =============================================================================

start_time = datetime.utcnow()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global orchestrator
    
    logger.info("Starting Agent API...")
    
    # Initialize configuration
    config = Config.from_environment()
    
    # Initialize orchestrator with all adapters
    orchestrator = Orchestrator(config)
    await orchestrator.initialize()
    
    logger.info(f"Agent API initialized (mode={config.mode.value})")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Agent API...")
    if orchestrator:
        await orchestrator.shutdown()


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Creative Ads Agent API",
    description="API for the Creative Ads Scraping and Reverse-Prompting Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for Cloud Run."""
    uptime = (datetime.utcnow() - start_time).total_seconds()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=uptime
    )


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Readiness check endpoint."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return {"status": "ready"}


# =============================================================================
# Dashboard Integration Endpoint
# =============================================================================

@app.post("/api/v1/jobs/trigger", response_model=JobTriggerResponse, tags=["Dashboard"])
async def trigger_job_from_dashboard(
    request: JobTriggerRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger a job from the dashboard.
    
    This endpoint is called by the dashboard when a user initiates
    a job through the Pipeline Control Panel.
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    logger.info(f"Received job trigger from dashboard: {request.job_id} ({request.job_type})")
    
    agent = orchestrator.get_agent()
    
    # Emit event that we received the job
    await orchestrator.emit_event(
        "job_received",
        {
            "message": f"Agent received {request.job_type} job",
            "job_type": request.job_type,
            "payload": request.payload,
        },
        job_id=request.job_id
    )
    
    # Process the job based on type
    try:
        if request.job_type == "scrape":
            # Queue scraping job
            sources = request.payload.get("sources", ["meta_ad_library"])
            query = request.payload.get("query")
            limit = request.payload.get("limit", 50)
            
            await orchestrator.emit_step_started(request.job_id, "scrape", f"Starting scrape for {len(sources)} source(s)")
            
            # Trigger scraping in background
            background_tasks.add_task(
                _run_scraping_job,
                request.job_id,
                sources,
                query,
                limit
            )
            
        elif request.job_type == "extract_features":
            asset_ids = request.payload.get("asset_ids")
            await orchestrator.emit_step_started(request.job_id, "extract", "Starting feature extraction")
            
            background_tasks.add_task(
                _run_extraction_job,
                request.job_id,
                asset_ids
            )
            
        elif request.job_type == "generate_prompt":
            asset_ids = request.payload.get("asset_ids")
            await orchestrator.emit_step_started(request.job_id, "generate", "Starting prompt generation")
            
            background_tasks.add_task(
                _run_generation_job,
                request.job_id,
                asset_ids
            )
            
        elif request.job_type in ["classify", "classify_industry"]:
            asset_ids = request.payload.get("asset_ids")
            await orchestrator.emit_step_started(request.job_id, "classify", "Starting classification")
            
            background_tasks.add_task(
                _run_classification_job,
                request.job_id,
                asset_ids
            )
            
        elif request.job_type == "full_pipeline":
            sources = request.payload.get("sources", ["meta_ad_library"])
            query = request.payload.get("query")
            limit = request.payload.get("limit", 50)
            skip_steps = request.payload.get("skip_steps", [])
            
            await orchestrator.emit_pipeline_started(
                request.job_id,
                sources,
                query,
                [s for s in ["scrape", "extract", "generate", "classify"] if s not in skip_steps]
            )
            
            background_tasks.add_task(
                _run_full_pipeline,
                request.job_id,
                sources,
                query,
                limit,
                skip_steps
            )
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown job type: {request.job_type}")
        
        return JobTriggerResponse(
            status="accepted",
            message=f"Job {request.job_type} accepted for processing",
            job_id=request.job_id
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger job: {e}")
        await orchestrator.emit_error(request.job_id, request.job_type, str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Background job runners
async def _run_scraping_job(job_id: str, sources: List[str], query: Optional[str], limit: int):
    """Run a scraping job in the background."""
    try:
        # Simulate scraping progress
        for i, source in enumerate(sources):
            progress = ((i + 1) / len(sources)) * 100
            await orchestrator.emit_step_progress(job_id, "scrape", progress, f"Scraping {source}...")
            await asyncio.sleep(0.5)  # Placeholder for actual scraping
        
        await orchestrator.emit_step_completed(job_id, "scrape", {
            "sources": sources,
            "items_scraped": 0,  # Will be real count
        })
    except Exception as e:
        logger.error(f"Scraping job failed: {e}")
        await orchestrator.emit_error(job_id, "scrape", str(e))


async def _run_extraction_job(job_id: str, asset_ids: Optional[List[str]]):
    """Run a feature extraction job in the background."""
    try:
        await orchestrator.emit_step_progress(job_id, "extract", 50, "Extracting features...")
        await asyncio.sleep(0.5)  # Placeholder
        await orchestrator.emit_step_completed(job_id, "extract", {"assets_processed": 0})
    except Exception as e:
        logger.error(f"Extraction job failed: {e}")
        await orchestrator.emit_error(job_id, "extract", str(e))


async def _run_generation_job(job_id: str, asset_ids: Optional[List[str]]):
    """Run a prompt generation job in the background."""
    try:
        await orchestrator.emit_step_progress(job_id, "generate", 50, "Generating prompts...")
        await asyncio.sleep(0.5)  # Placeholder
        await orchestrator.emit_step_completed(job_id, "generate", {"prompts_generated": 0})
    except Exception as e:
        logger.error(f"Generation job failed: {e}")
        await orchestrator.emit_error(job_id, "generate", str(e))


async def _run_classification_job(job_id: str, asset_ids: Optional[List[str]]):
    """Run a classification job in the background."""
    try:
        await orchestrator.emit_step_progress(job_id, "classify", 50, "Classifying assets...")
        await asyncio.sleep(0.5)  # Placeholder
        await orchestrator.emit_step_completed(job_id, "classify", {"assets_classified": 0})
    except Exception as e:
        logger.error(f"Classification job failed: {e}")
        await orchestrator.emit_error(job_id, "classify", str(e))


async def _run_full_pipeline(
    job_id: str,
    sources: List[str],
    query: Optional[str],
    limit: int,
    skip_steps: List[str]
):
    """Run a full pipeline job in the background."""
    import time
    start_time = time.time()
    
    try:
        steps = ["scrape", "extract", "generate", "classify"]
        active_steps = [s for s in steps if s not in skip_steps]
        
        for i, step in enumerate(active_steps):
            await orchestrator.emit_step_started(job_id, step, f"Starting {step}...")
            
            # Simulate step progress
            for p in range(0, 101, 25):
                await orchestrator.emit_step_progress(job_id, step, p, f"{step}: {p}%")
                await asyncio.sleep(0.2)
            
            await orchestrator.emit_step_completed(job_id, step, {"completed": True})
        
        duration = time.time() - start_time
        await orchestrator.emit_pipeline_completed(job_id, duration, 0, 0)
        
    except Exception as e:
        logger.error(f"Pipeline job failed: {e}")
        await orchestrator.emit_error(job_id, "pipeline", str(e))


# =============================================================================
# Scraping Endpoints
# =============================================================================

@app.post("/trigger", response_model=TriggerScrapingResponse, tags=["Scraping"])
async def trigger_full_pipeline(
    request: TriggerScrapingRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger a full scraping pipeline across specified sources.
    
    This endpoint queues scraping jobs for all specified sources
    (or all available sources if none specified).
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    agent = orchestrator.get_agent()
    
    # Parse sources
    sources = None
    if request.sources:
        try:
            sources = [ScraperSource(s) for s in request.sources]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid source: {e}")
    
    # Parse industries
    industries = None
    if request.industries:
        try:
            industries = [IndustryCategory(i) for i in request.industries]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid industry: {e}")
    
    # Trigger pipeline
    result = await agent.trigger_full_pipeline(
        sources=sources,
        industries=industries,
        max_items_per_source=request.max_items_per_source
    )
    
    return TriggerScrapingResponse(
        triggered=result["triggered"],
        job_ids=result["job_ids"],
        sources=result["sources"],
        message=f"Triggered {len(result['job_ids'])} scraping jobs"
    )


@app.post("/scrape", response_model=ScrapingJobResponse, tags=["Scraping"])
async def create_scraping_job(request: ScrapingJobRequest):
    """
    Create a single scraping job for a specific source.
    """
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    # Validate source
    try:
        source = ScraperSource(request.source)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source. Must be one of: {[s.value for s in ScraperSource]}"
        )
    
    # Create job
    queue = orchestrator.get_queue()
    job_id = await queue.create_scrape_job(
        source=request.source,
        query=request.query,
        filters={
            **(request.filters or {}),
            "max_items": request.max_items
        }
    )
    
    return ScrapingJobResponse(
        job_id=job_id,
        status="queued",
        message=f"Scraping job created for {request.source}"
    )


@app.get("/sources", tags=["Scraping"])
async def list_sources():
    """List available scraping sources."""
    return {
        "sources": [
            {
                "id": source.value,
                "name": source.name.replace("_", " ").title(),
                "enabled": True
            }
            for source in ScraperSource
        ]
    }


# =============================================================================
# Status Endpoints
# =============================================================================

@app.get("/status", response_model=PipelineStatusResponse, tags=["Status"])
async def get_pipeline_status():
    """Get current pipeline status."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    agent = orchestrator.get_agent()
    status = await agent.get_pipeline_status()
    
    return PipelineStatusResponse(
        running=status["running"],
        active_tasks=status["active_tasks"],
        metrics=status["metrics"],
        queue=status["queue"],
        last_updated=status["last_updated"]
    )


@app.get("/metrics", response_model=MetricsResponse, tags=["Status"])
async def get_metrics():
    """Get pipeline metrics."""
    if orchestrator is None:
        return MetricsResponse(
            assets_scraped=0,
            features_extracted=0,
            prompts_generated=0,
            assets_stored=0,
            errors=0,
            by_source={},
            by_industry={}
        )
    
    agent = orchestrator.get_agent()
    status = await agent.get_pipeline_status()
    metrics = status.get("metrics", {})
    
    return MetricsResponse(
        assets_scraped=metrics.get("assets_scraped", 0),
        features_extracted=metrics.get("features_extracted", 0),
        prompts_generated=metrics.get("prompts_generated", 0),
        assets_stored=metrics.get("assets_stored", 0),
        errors=metrics.get("errors", 0),
        by_source=agent._metrics.source_metrics if agent else {},
        by_industry=agent._metrics.industry_metrics if agent else {}
    )


@app.get("/queue/size", tags=["Status"])
async def get_queue_size():
    """Get current job queue size."""
    if orchestrator is None:
        return {"size": 0}
    
    queue = orchestrator.get_queue()
    return {"size": queue.get_queue_size()}


@app.get("/queue/metrics", tags=["Status"])
async def get_queue_metrics():
    """Get detailed queue metrics."""
    if orchestrator is None:
        return {}
    
    queue = orchestrator.get_queue()
    metrics = queue.get_metrics()
    return {
        "total_jobs": metrics.total_jobs,
        "pending_jobs": metrics.pending_jobs,
        "in_progress_jobs": metrics.in_progress_jobs,
        "completed_jobs": metrics.completed_jobs,
        "failed_jobs": metrics.failed_jobs,
        "dead_letter_jobs": metrics.dead_letter_jobs,
        "avg_processing_time_seconds": metrics.avg_processing_time_seconds
    }


# =============================================================================
# Industry Endpoints
# =============================================================================

@app.get("/industries", tags=["Classification"])
async def list_industries():
    """List available industry categories."""
    return {
        "industries": [
            {
                "id": industry.value,
                "name": industry.name.replace("_", " ").title()
            }
            for industry in IndustryCategory
        ]
    }


# =============================================================================
# Admin Endpoints
# =============================================================================

@app.post("/admin/clear-queue", tags=["Admin"])
async def clear_queue():
    """Clear the job queue (development only)."""
    if orchestrator is None:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    # Only allow in local mode
    if not orchestrator.config.is_local:
        raise HTTPException(
            status_code=403,
            detail="Queue clearing not allowed in cloud mode"
        )
    
    # Clear local queue
    queue = orchestrator.get_queue()
    if hasattr(queue, '_queue'):
        queue._queue.clear()
    
    return {"message": "Queue cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

