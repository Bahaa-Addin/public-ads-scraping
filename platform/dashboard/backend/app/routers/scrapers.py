"""
Scrapers API Router

Endpoints for scraper monitoring and control.
"""

import httpx
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends

from ..config import get_settings
from ..models import (
    ScraperSource, ScraperStatus, ScraperMetrics,
    ScraperTriggerRequest, ScraperTriggerResponse, IndustryCategory
)
from ..services.job_service import JobService, get_job_service
from ..services.metrics_service import MetricsService, get_metrics_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scrapers", tags=["Scrapers"])


@router.get("/sources")
async def list_sources():
    """List all available scraper sources."""
    return {
        "sources": [
            {
                "id": source.value,
                "name": source.name.replace("_", " ").title(),
                "description": _get_source_description(source),
                "enabled": True
            }
            for source in ScraperSource
        ]
    }


@router.get("/status", response_model=List[ScraperStatus])
async def get_scraper_statuses(
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get status of all scrapers."""
    return await metrics_service.get_scraper_statuses()


@router.get("/status/{source}", response_model=ScraperStatus)
async def get_scraper_status(
    source: ScraperSource,
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get status of a specific scraper."""
    statuses = await metrics_service.get_scraper_statuses()
    for status in statuses:
        if status.source == source:
            return status
    raise HTTPException(status_code=404, detail="Scraper not found")


@router.get("/metrics", response_model=List[ScraperMetrics])
async def get_scraper_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get detailed metrics for all scrapers."""
    return await metrics_service.get_scraper_metrics()


@router.post("/trigger", response_model=ScraperTriggerResponse)
async def trigger_scraping(
    request: ScraperTriggerRequest,
    job_service: JobService = Depends(get_job_service)
):
    """
    Trigger scraping jobs for specified sources.
    
    Creates scraping jobs and publishes them to the job queue.
    """
    if not request.sources:
        raise HTTPException(status_code=400, detail="At least one source required")
    
    return await job_service.trigger_scraping(request)


@router.post("/trigger/{source}", response_model=ScraperTriggerResponse)
async def trigger_single_scraper(
    source: ScraperSource,
    query: Optional[str] = None,
    max_items: int = 100,
    job_service: JobService = Depends(get_job_service)
):
    """Trigger a single scraper source."""
    request = ScraperTriggerRequest(
        sources=[source],
        query=query,
        max_items_per_source=max_items
    )
    return await job_service.trigger_scraping(request)


@router.post("/trigger-all", response_model=ScraperTriggerResponse)
async def trigger_all_scrapers(
    query: Optional[str] = None,
    max_items_per_source: int = 50,
    industries: Optional[List[IndustryCategory]] = None,
    job_service: JobService = Depends(get_job_service)
):
    """Trigger all enabled scrapers."""
    request = ScraperTriggerRequest(
        sources=list(ScraperSource),
        query=query,
        max_items_per_source=max_items_per_source,
        industries=industries
    )
    return await job_service.trigger_scraping(request)


@router.post("/{source}/enable")
async def enable_scraper(source: ScraperSource):
    """Enable a scraper source."""
    # In production, this would update configuration in Firestore/config
    return {"message": f"Enabled scraper: {source.value}", "source": source.value, "enabled": True}


@router.post("/{source}/disable")
async def disable_scraper(source: ScraperSource):
    """Disable a scraper source."""
    # In production, this would update configuration in Firestore/config
    return {"message": f"Disabled scraper: {source.value}", "source": source.value, "enabled": False}


def _get_source_description(source: ScraperSource) -> str:
    """Get description for a scraper source."""
    descriptions = {
        ScraperSource.META_AD_LIBRARY: "Facebook and Instagram ads from Meta Ad Library",
        ScraperSource.GOOGLE_ADS_TRANSPARENCY: "Google Display ads from Transparency Center",
        ScraperSource.INTERNET_ARCHIVE: "Historical TV advertisements from Internet Archive",
        ScraperSource.WIKIMEDIA_COMMONS: "Public domain creative assets from Wikimedia"
    }
    return descriptions.get(source, "No description available")


@router.get("/active")
async def get_active_scrapers():
    """
    Get list of active scraper streaming sessions.
    
    Proxies to the Node.js scraper service to get currently running 
    scraper sessions that are streaming video.
    """
    settings = get_settings()
    scraper_url = settings.scraper_api_url
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{scraper_url}/sessions/active")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Scraper service returned status {response.status_code}")
                return {"sessions": []}
    except httpx.RequestError as e:
        logger.debug(f"Could not connect to scraper service: {e}")
        return {"sessions": []}


@router.get("/sessions/with-screenshots")
async def get_sessions_with_screenshots():
    """
    Get list of session IDs that have screenshots available for replay.
    
    Proxies to the Node.js scraper service.
    """
    settings = get_settings()
    scraper_url = settings.scraper_api_url
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{scraper_url}/sessions/with-screenshots")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Scraper service returned status {response.status_code}")
                return {"sessions": [], "count": 0}
    except httpx.RequestError as e:
        logger.debug(f"Could not connect to scraper service: {e}")
        return {"sessions": [], "count": 0}


@router.get("/sessions/{session_id}/screenshots")
async def get_session_screenshots(session_id: str):
    """
    Get list of screenshots for a specific session.
    
    Proxies to the Node.js scraper service.
    """
    settings = get_settings()
    scraper_url = settings.scraper_api_url
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{scraper_url}/sessions/{session_id}/screenshots")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Scraper service returned status {response.status_code}")
                return {"session_id": session_id, "count": 0, "screenshots": []}
    except httpx.RequestError as e:
        logger.debug(f"Could not connect to scraper service: {e}")
        return {"session_id": session_id, "count": 0, "screenshots": []}

