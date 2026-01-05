"""
Logs API Router

Endpoints for log viewing and searching.
"""

import random
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Query, Depends

from ..models import LogEntry, LogLevel, LogSearchParams, LogSearchResponse

router = APIRouter(prefix="/logs", tags=["Logs"])


def _generate_mock_logs(count: int = 100) -> List[LogEntry]:
    """Generate mock log entries for development."""
    log_messages = {
        LogLevel.INFO: [
            "Scraped 25 assets from meta_ad_library",
            "Feature extraction completed for asset-123",
            "Reverse prompt generated successfully",
            "Job completed in 5.2 seconds",
            "Worker started processing job queue",
            "Health check passed",
            "Batch processing started with 50 items",
        ],
        LogLevel.WARNING: [
            "Rate limit approaching for meta_ad_library",
            "Slow response from Vertex AI (3.5s)",
            "Queue backlog increasing",
            "Retrying failed job (attempt 2/3)",
            "Memory usage above 80%",
        ],
        LogLevel.ERROR: [
            "Failed to scrape: Rate limit exceeded",
            "Feature extraction timeout",
            "Vertex AI API error: 503 Service Unavailable",
            "Failed to store asset in Cloud Storage",
            "Job moved to dead letter queue",
        ],
        LogLevel.DEBUG: [
            "Processing job: scrape-abc123",
            "Loaded image: 1024x768 pixels",
            "Color extraction: found 5 dominant colors",
            "CTA detected: 'Shop Now' at bottom",
        ]
    }
    
    sources = ["agent_brain", "scraper", "feature_extraction", "reverse_prompt", "storage", "job_queue"]
    
    logs = []
    now = datetime.utcnow()
    
    for i in range(count):
        level = random.choices(
            [LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.DEBUG],
            weights=[0.6, 0.2, 0.1, 0.1]
        )[0]
        
        logs.append(LogEntry(
            timestamp=now - timedelta(minutes=i * random.randint(1, 5)),
            level=level,
            message=random.choice(log_messages[level]),
            source=random.choice(sources),
            job_id=f"job-{random.randint(1, 50)}" if random.random() > 0.3 else None,
            asset_id=f"asset-{random.randint(1, 100)}" if random.random() > 0.5 else None,
            metadata={
                "duration_ms": random.randint(100, 5000),
                "worker_id": f"worker-{random.randint(0, 9)}"
            } if random.random() > 0.7 else None
        ))
    
    return logs


# Cache mock logs
_mock_logs = _generate_mock_logs(500)


@router.get("", response_model=LogSearchResponse)
async def search_logs(
    job_id: Optional[str] = None,
    asset_id: Optional[str] = None,
    level: Optional[LogLevel] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200)
):
    """
    Search and filter logs.
    
    In production, this would query Cloud Logging or a log aggregation service.
    """
    logs = _mock_logs.copy()
    
    # Apply filters
    if job_id:
        logs = [l for l in logs if l.job_id == job_id]
    if asset_id:
        logs = [l for l in logs if l.asset_id == asset_id]
    if level:
        logs = [l for l in logs if l.level == level]
    if source:
        logs = [l for l in logs if l.source == source]
    if search:
        search_lower = search.lower()
        logs = [l for l in logs if search_lower in l.message.lower()]
    if start_time:
        logs = [l for l in logs if l.timestamp >= start_time]
    if end_time:
        logs = [l for l in logs if l.timestamp <= end_time]
    
    # Sort by timestamp descending
    logs.sort(key=lambda x: x.timestamp, reverse=True)
    
    # Paginate
    total = len(logs)
    start = (page - 1) * page_size
    end = start + page_size
    page_logs = logs[start:end]
    
    return LogSearchResponse(
        logs=page_logs,
        total=total,
        has_more=(page * page_size) < total
    )


@router.get("/job/{job_id}", response_model=LogSearchResponse)
async def get_logs_for_job(
    job_id: str,
    level: Optional[LogLevel] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200)
):
    """Get all logs for a specific job."""
    return await search_logs(
        job_id=job_id,
        level=level,
        page=page,
        page_size=page_size
    )


@router.get("/asset/{asset_id}", response_model=LogSearchResponse)
async def get_logs_for_asset(
    asset_id: str,
    level: Optional[LogLevel] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200)
):
    """Get all logs for a specific asset."""
    return await search_logs(
        asset_id=asset_id,
        level=level,
        page=page,
        page_size=page_size
    )


@router.get("/errors", response_model=LogSearchResponse)
async def get_error_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200)
):
    """Get only error and critical logs."""
    logs = [l for l in _mock_logs if l.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
    logs.sort(key=lambda x: x.timestamp, reverse=True)
    
    total = len(logs)
    start = (page - 1) * page_size
    end = start + page_size
    
    return LogSearchResponse(
        logs=logs[start:end],
        total=total,
        has_more=(page * page_size) < total
    )


@router.get("/sources")
async def get_log_sources():
    """Get list of available log sources."""
    sources = set(l.source for l in _mock_logs if l.source)
    return {"sources": sorted(sources)}


@router.get("/stats")
async def get_log_stats():
    """Get log statistics."""
    level_counts = {}
    source_counts = {}
    
    for log in _mock_logs:
        level_counts[log.level.value] = level_counts.get(log.level.value, 0) + 1
        if log.source:
            source_counts[log.source] = source_counts.get(log.source, 0) + 1
    
    return {
        "total_logs": len(_mock_logs),
        "by_level": level_counts,
        "by_source": source_counts
    }

