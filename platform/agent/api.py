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
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .agent_brain import AgentBrain, ScrapingTask, PipelineStage
from .config import Config, ScraperSource, IndustryCategory
from .orchestrator import Orchestrator
from .services import StreamManager, ScreenshotSaver
from .data_service import DataService, get_data_service

logger = logging.getLogger(__name__)

# Global instances
orchestrator: Optional[Orchestrator] = None
stream_manager: Optional[StreamManager] = None
screenshot_saver: Optional[ScreenshotSaver] = None
data_service: Optional[DataService] = None


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
    global orchestrator, stream_manager, screenshot_saver, data_service
    
    logger.info("Starting Agent API...")
    
    # Initialize configuration
    config = Config.from_environment()
    
    # Initialize data service for persistence
    data_service = get_data_service(config.data_dir)
    logger.info(f"DataService initialized with data_dir: {config.data_dir}")
    
    # Initialize screenshot saver and stream manager
    screenshot_saver = ScreenshotSaver(base_path=f"{config.data_dir}/screenshots")
    stream_manager = StreamManager(
        screenshot_saver=screenshot_saver,
        screenshot_interval_seconds=2.0,
        frame_quality=60,
        max_width=1280,
        max_height=720,
    )
    
    # Initialize orchestrator with all adapters
    orchestrator = Orchestrator(config)
    await orchestrator.initialize()
    
    # Attach stream manager to orchestrator
    orchestrator.set_stream_manager(stream_manager)
    
    logger.info(f"Agent API initialized (mode={config.mode.value})")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Agent API...")
    if stream_manager:
        await stream_manager.shutdown()
    if orchestrator:
        await orchestrator.shutdown()


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Agentic Ads Agent API",
    description="API for the Agentic Ads Scraping and Reverse-Prompting Platform",
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
    """Run a scraping job in the background by calling the Node.js scraper service."""
    total_items_scraped = 0
    all_assets = []
    
    # #region agent log
    import json as _json; open('/Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/.cursor/debug.log','a').write(_json.dumps({"location":"api.py:_run_scraping_job","message":"Scraping job started","data":{"job_id":job_id,"sources":sources,"query":query,"limit":limit},"timestamp":datetime.utcnow().isoformat(),"hypothesisId":"H-scrape-execution"})+"\n")
    # #endregion
    
    try:
        # Update job status to in_progress
        if data_service:
            data_service.update_job_status(job_id, "in_progress")
            # #region agent log
            import json as _json; open('/Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/.cursor/debug.log','a').write(_json.dumps({"location":"api.py:_run_scraping_job","message":"Updated job to in_progress","data":{"job_id":job_id},"timestamp":datetime.utcnow().isoformat(),"hypothesisId":"H-job-status-update"})+"\n")
            # #endregion
        
        config = orchestrator.config
        scraper_url = config.scraper_api_url
        
        for i, source in enumerate(sources):
            session_id = str(uuid.uuid4())
            
            # Mark scraper as running
            if data_service:
                data_service.set_scraper_running(source, True)
            
            await orchestrator.emit_step_progress(
                job_id, "scrape", 
                ((i) / len(sources)) * 100, 
                f"Starting scrape for {source}..."
            )
            
            # Emit session started event for live view
            await orchestrator.emit_event(
                "scraper_session_started",
                {
                    "session_id": session_id,
                    "job_id": job_id,
                    "source": source,
                    "message": f"Starting {source} scraper with live streaming"
                },
                job_id=job_id
            )
            
            source_success = False
            source_error = None
            
            try:
                # Call Node.js scraper service
                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.post(
                        f"{scraper_url}/scrape",
                        json={
                            "source": source,
                            "query": query,
                            "maxItems": limit,
                            "streaming": True,
                            "sessionId": session_id,
                            "jobId": job_id,
                            "headless": True  # Use headless mode for production
                        }
                    )
                    
                    # #region agent log
                    import json as _json; open('/Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/.cursor/debug.log','a').write(_json.dumps({"location":"api.py:_run_scraping_job","message":"Scraper response received","data":{"job_id":job_id,"source":source,"status_code":response.status_code},"timestamp":datetime.utcnow().isoformat(),"hypothesisId":"H-scraper-response"})+"\n")
                    # #endregion
                    
                    if response.status_code == 200:
                        result = response.json()
                        assets = result.get("assets", [])
                        items_scraped = len(assets)
                        total_items_scraped += items_scraped
                        all_assets.extend(assets)
                        source_success = True
                        
                        # #region agent log
                        import json as _json; open('/Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/.cursor/debug.log','a').write(_json.dumps({"location":"api.py:_run_scraping_job","message":"Assets scraped","data":{"job_id":job_id,"source":source,"items_scraped":items_scraped,"total_items":total_items_scraped},"timestamp":datetime.utcnow().isoformat(),"hypothesisId":"H-scraper-assets"})+"\n")
                        # #endregion
                        
                        logger.info(f"Scraped {items_scraped} items from {source}")
                        
                        # Save assets to persistent storage
                        if data_service and assets:
                            saved_count = data_service.save_assets(assets, source)
                            logger.info(f"Saved {saved_count} assets to storage")
                        
                        await orchestrator.emit_step_progress(
                            job_id, "scrape",
                            ((i + 1) / len(sources)) * 100,
                            f"Scraped {items_scraped} items from {source}"
                        )
                        
                        # Emit individual asset events for timeline
                        for asset in assets[:5]:  # First 5 for timeline preview
                            await orchestrator.emit_event(
                                "asset_scraped",
                                {
                                    "asset_id": asset.get("id"),
                                    "source": source,
                                    "image_url": asset.get("imageUrl"),
                                    "title": asset.get("title"),
                                },
                                job_id=job_id
                            )
                    else:
                        source_error = f"Scraper returned status {response.status_code}"
                        logger.error(source_error)
                        await orchestrator.emit_event(
                            "scraper_error",
                            {"source": source, "error": source_error},
                            job_id=job_id
                        )
                        
            except httpx.ConnectError:
                source_error = f"Could not connect to scraper service at {scraper_url}"
                logger.error(source_error)
                await orchestrator.emit_event(
                    "scraper_error",
                    {"source": source, "error": source_error},
                    job_id=job_id
                )
            except httpx.TimeoutException:
                source_error = f"Scraper request timed out for {source}"
                logger.error(source_error)
                await orchestrator.emit_event(
                    "scraper_error",
                    {"source": source, "error": source_error},
                    job_id=job_id
                )
            finally:
                # Update scraper metrics
                if data_service:
                    data_service.update_scraper_status(
                        source,
                        items_scraped=len([a for a in all_assets if a.get("source") == source or source in str(a)]),
                        success=source_success,
                        error_message=source_error
                    )
                
                # Emit session ended event
                await orchestrator.emit_event(
                    "scraper_session_ended",
                    {
                        "session_id": session_id,
                        "job_id": job_id,
                        "source": source,
                    },
                    job_id=job_id
                )
        
        # Update system metrics
        if data_service:
            data_service.update_system_metrics(assets_scraped=total_items_scraped)
            data_service.add_time_series_point("assets_scraped", total_items_scraped)
        
        # Update job as completed
        if data_service:
            data_service.update_job_status(job_id, "completed", assets_processed=total_items_scraped)
            data_service.write_log("info", f"Scraping completed: {total_items_scraped} items from {len(sources)} source(s)", "agent", job_id)
        
        await orchestrator.emit_step_completed(job_id, "scrape", {
            "sources": sources,
            "items_scraped": total_items_scraped,
        })
        
    except Exception as e:
        logger.error(f"Scraping job failed: {e}")
        # Update job as failed
        if data_service:
            data_service.update_job_status(job_id, "failed", error_message=str(e))
        await orchestrator.emit_error(job_id, "scrape", str(e))


async def _run_extraction_job(job_id: str, asset_ids: Optional[List[str]]):
    """Run a feature extraction job in the background."""
    try:
        if data_service:
            data_service.update_job_status(job_id, "in_progress")
        
        await orchestrator.emit_step_progress(job_id, "extract", 25, "Loading assets...")
        await asyncio.sleep(0.5)
        
        await orchestrator.emit_step_progress(job_id, "extract", 50, "Extracting features...")
        await asyncio.sleep(0.5)
        
        await orchestrator.emit_step_progress(job_id, "extract", 75, "Saving features...")
        await asyncio.sleep(0.5)
        
        # Mark job as completed
        if data_service:
            data_service.update_job_status(job_id, "completed", assets_processed=0)
        
        await orchestrator.emit_step_completed(job_id, "extract", {"assets_processed": 0})
    except Exception as e:
        logger.error(f"Extraction job failed: {e}")
        if data_service:
            data_service.update_job_status(job_id, "failed", error_message=str(e))
        await orchestrator.emit_error(job_id, "extract", str(e))


async def _run_generation_job(job_id: str, asset_ids: Optional[List[str]]):
    """Run a prompt generation job in the background."""
    try:
        if data_service:
            data_service.update_job_status(job_id, "in_progress")
        
        await orchestrator.emit_step_progress(job_id, "generate", 25, "Loading features...")
        await asyncio.sleep(0.5)
        
        await orchestrator.emit_step_progress(job_id, "generate", 50, "Generating prompts...")
        await asyncio.sleep(0.5)
        
        await orchestrator.emit_step_progress(job_id, "generate", 75, "Saving prompts...")
        await asyncio.sleep(0.5)
        
        # Mark job as completed
        if data_service:
            data_service.update_job_status(job_id, "completed", assets_processed=0)
        
        await orchestrator.emit_step_completed(job_id, "generate", {"prompts_generated": 0})
    except Exception as e:
        logger.error(f"Generation job failed: {e}")
        if data_service:
            data_service.update_job_status(job_id, "failed", error_message=str(e))
        await orchestrator.emit_error(job_id, "generate", str(e))


async def _run_classification_job(job_id: str, asset_ids: Optional[List[str]]):
    """Run a classification job in the background."""
    try:
        if data_service:
            data_service.update_job_status(job_id, "in_progress")
        
        await orchestrator.emit_step_progress(job_id, "classify", 25, "Loading assets...")
        await asyncio.sleep(0.5)
        
        await orchestrator.emit_step_progress(job_id, "classify", 50, "Classifying assets...")
        await asyncio.sleep(0.5)
        
        await orchestrator.emit_step_progress(job_id, "classify", 75, "Saving classifications...")
        await asyncio.sleep(0.5)
        
        # Mark job as completed
        if data_service:
            data_service.update_job_status(job_id, "completed", assets_processed=0)
        
        await orchestrator.emit_step_completed(job_id, "classify", {"assets_classified": 0})
    except Exception as e:
        logger.error(f"Classification job failed: {e}")
        if data_service:
            data_service.update_job_status(job_id, "failed", error_message=str(e))
        await orchestrator.emit_error(job_id, "classify", str(e))


async def _run_full_pipeline(
    job_id: str,
    sources: List[str],
    query: Optional[str],
    limit: int,
    skip_steps: List[str]
):
    """Run a full pipeline job in the background with real scraping."""
    import time
    start_time = time.time()
    total_assets = 0
    
    # #region agent log
    import json as _json; open('/Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/.cursor/debug.log','a').write(_json.dumps({"location":"api.py:_run_full_pipeline","message":"Full pipeline started","data":{"job_id":job_id,"sources":sources,"skip_steps":skip_steps},"timestamp":datetime.utcnow().isoformat(),"hypothesisId":"H-full-pipeline"})+"\n")
    # #endregion
    
    try:
        # Update job status
        if data_service:
            data_service.update_job_status(job_id, "in_progress")
            data_service.write_log("info", f"Pipeline started for {len(sources)} source(s)", "agent", job_id)
            # #region agent log
            import json as _json; open('/Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/.cursor/debug.log','a').write(_json.dumps({"location":"api.py:_run_full_pipeline","message":"Job status updated to in_progress","data":{"job_id":job_id},"timestamp":datetime.utcnow().isoformat(),"hypothesisId":"H-full-pipeline-status"})+"\n")
            # #endregion
        
        steps = ["scrape", "extract", "generate", "classify"]
        active_steps = [s for s in steps if s not in skip_steps]
        
        for i, step in enumerate(active_steps):
            await orchestrator.emit_step_started(job_id, step, f"Starting {step}...")
            
            if step == "scrape":
                # Actually run the scraper
                config = orchestrator.config
                scraper_url = config.scraper_api_url
                # #region agent log
                import json as _json; open('/Users/monterey/Workspace/Projs/Tasmem/tasmem-scraping/.cursor/debug.log','a').write(_json.dumps({"location":"api.py:_run_full_pipeline","message":"Running scrape step","data":{"job_id":job_id,"scraper_url":scraper_url,"sources":sources},"timestamp":datetime.utcnow().isoformat(),"hypothesisId":"H-scrape-step"})+"\n")
                # #endregion
                
                for si, source in enumerate(sources):
                    session_id = str(uuid.uuid4())
                    
                    # Mark scraper as running
                    if data_service:
                        data_service.set_scraper_running(source, True)
                    
                    progress = int(((si) / len(sources)) * 100)
                    await orchestrator.emit_step_progress(job_id, "scrape", progress, f"Scraping {source}...")
                    
                    source_success = False
                    source_error = None
                    items_scraped = 0
                    
                    try:
                        async with httpx.AsyncClient(timeout=300.0) as client:
                            response = await client.post(
                                f"{scraper_url}/scrape",
                                json={
                                    "source": source,
                                    "query": query,
                                    "maxItems": limit,
                                    "streaming": True,
                                    "sessionId": session_id,
                                    "jobId": job_id,
                                    "headless": True
                                }
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                assets = result.get("assets", [])
                                items_scraped = len(assets)
                                total_assets += items_scraped
                                source_success = True
                                
                                # Save assets
                                if data_service and assets:
                                    data_service.save_assets(assets, source)
                                
                                # Emit asset events
                                for asset in assets[:3]:
                                    await orchestrator.emit_event(
                                        "asset_scraped",
                                        {
                                            "asset_id": asset.get("id"),
                                            "source": source,
                                            "image_url": asset.get("imageUrl"),
                                        },
                                        job_id=job_id
                                    )
                            else:
                                source_error = f"Scraper returned {response.status_code}"
                                
                    except httpx.ConnectError:
                        source_error = f"Could not connect to scraper at {scraper_url}"
                    except httpx.TimeoutException:
                        source_error = "Scraper timed out"
                    except Exception as e:
                        source_error = str(e)
                    finally:
                        # Update scraper metrics
                        if data_service:
                            data_service.update_scraper_status(source, items_scraped, source_success, source_error)
                    
                    if source_error:
                        await orchestrator.emit_event("scraper_error", {"source": source, "error": source_error}, job_id=job_id)
                
                # Update metrics
                if data_service:
                    data_service.update_system_metrics(assets_scraped=total_assets)
                    data_service.add_time_series_point("assets_scraped", total_assets)
                
                await orchestrator.emit_step_completed(job_id, "scrape", {"items_scraped": total_assets})
                
            else:
                # Other steps use placeholder logic for now
                for p in [25, 50, 75, 100]:
                    await orchestrator.emit_step_progress(job_id, step, p, f"{step}: {p}%")
                    await asyncio.sleep(0.3)
                
                await orchestrator.emit_step_completed(job_id, step, {"completed": True})
        
        duration = time.time() - start_time
        
        # Update job status to completed
        if data_service:
            data_service.update_job_status(job_id, "completed", assets_processed=total_assets)
            data_service.write_log("info", f"Pipeline completed in {duration:.1f}s with {total_assets} assets", "agent", job_id)
        
        await orchestrator.emit_pipeline_completed(job_id, duration, total_assets, 0)
        
    except Exception as e:
        logger.error(f"Pipeline job failed: {e}")
        if data_service:
            data_service.update_job_status(job_id, "failed", error_message=str(e))
            data_service.write_log("error", f"Pipeline failed: {str(e)}", "agent", job_id)
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


# =============================================================================
# Live Streaming Endpoints (WebSocket)
# =============================================================================

@app.websocket("/ws/scraper/{session_id}")
async def scraper_stream(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for live scraper video stream.
    
    Clients connect to this endpoint to receive real-time video frames
    from an active scraper session.
    """
    if stream_manager is None:
        await websocket.close(code=1011, reason="Stream manager not initialized")
        return
    
    await websocket.accept()
    logger.info(f"WebSocket connected for session {session_id}")
    
    # Subscribe to the stream
    stream_manager.subscribe(session_id, websocket)
    
    # Send initial session info if available
    session_info = stream_manager.get_session(session_id)
    if session_info:
        await websocket.send_json({
            "type": "session_info",
            "session": session_info,
        })
    else:
        await websocket.send_json({
            "type": "waiting",
            "message": f"Waiting for session {session_id} to start...",
        })
    
    try:
        while True:
            # Keep connection alive by receiving pings/messages
            data = await websocket.receive_text()
            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        stream_manager.unsubscribe(session_id, websocket)


@app.get("/api/v1/scrapers/active", tags=["Streaming"])
async def get_active_scrapers():
    """Get list of active scraper streaming sessions."""
    if stream_manager is None:
        return {"sessions": []}
    
    return {"sessions": stream_manager.get_active_sessions()}


@app.get("/api/v1/scrapers/{session_id}", tags=["Streaming"])
async def get_scraper_session(session_id: str):
    """Get info about a specific scraper session."""
    if stream_manager is None:
        raise HTTPException(status_code=503, detail="Stream manager not initialized")
    
    session = stream_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


# =============================================================================
# Screenshot Endpoints (Job Replay)
# =============================================================================

@app.get("/api/v1/jobs/{job_id}/screenshots", tags=["Screenshots"])
async def get_job_screenshots(job_id: str):
    """
    Get list of screenshots for a job.
    
    Returns a list of screenshot metadata including URLs for playback.
    """
    if screenshot_saver is None:
        raise HTTPException(status_code=503, detail="Screenshot saver not initialized")
    
    screenshots = screenshot_saver.get_job_screenshots(job_id)
    return {
        "job_id": job_id,
        "count": len(screenshots),
        "screenshots": screenshots,
    }


@app.get("/api/v1/screenshots/{job_id}/{filename}", tags=["Screenshots"])
async def get_screenshot(job_id: str, filename: str):
    """
    Serve a screenshot image file.
    
    Returns the JPEG image for display in the replay player.
    """
    if screenshot_saver is None:
        raise HTTPException(status_code=503, detail="Screenshot saver not initialized")
    
    # Validate filename to prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    path = screenshot_saver.get_screenshot_path(job_id, filename)
    if not path:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    
    return FileResponse(path, media_type="image/jpeg")


@app.get("/api/v1/jobs/with-screenshots", tags=["Screenshots"])
async def get_jobs_with_screenshots():
    """Get list of job IDs that have screenshots available."""
    if screenshot_saver is None:
        return {"jobs": []}
    
    jobs = screenshot_saver.get_all_jobs_with_screenshots()
    return {"jobs": jobs, "count": len(jobs)}


@app.delete("/api/v1/jobs/{job_id}/screenshots", tags=["Screenshots"])
async def delete_job_screenshots(job_id: str):
    """Delete all screenshots for a job."""
    if screenshot_saver is None:
        raise HTTPException(status_code=503, detail="Screenshot saver not initialized")
    
    success = screenshot_saver.delete_job_screenshots(job_id)
    if success:
        return {"message": f"Screenshots deleted for job {job_id}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to delete screenshots")


@app.get("/api/v1/screenshots/storage", tags=["Screenshots"])
async def get_screenshot_storage():
    """Get total storage used by screenshots."""
    if screenshot_saver is None:
        return {"bytes": 0, "mb": 0}
    
    total_bytes = screenshot_saver.get_total_storage_bytes()
    return {
        "bytes": total_bytes,
        "mb": round(total_bytes / (1024 * 1024), 2),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

