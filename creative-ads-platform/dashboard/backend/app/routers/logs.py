"""
Logs API Router

Endpoints for log viewing, searching, and writing.
In local mode, reads from local log files instead of Cloud Logging.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ..config import get_settings
from ..models import LogEntry, LogLevel, LogSearchResponse

router = APIRouter(prefix="/logs", tags=["Logs"])


class LogWriteRequest(BaseModel):
    """Request model for writing a log entry."""
    level: LogLevel
    message: str
    source: str
    job_id: Optional[str] = None
    asset_id: Optional[str] = None
    metadata: Optional[dict] = None


def _get_log_path() -> Path:
    """Get the path to the pipeline log file."""
    settings = get_settings()
    data_dir = settings.data_dir
    if not os.path.isabs(data_dir):
        # Relative to the backend app directory
        backend_dir = Path(__file__).parent.parent.parent
        data_dir = backend_dir / data_dir
    return Path(data_dir) / "logs" / "pipeline.log"


def _load_logs() -> List[LogEntry]:
    """Load logs from the pipeline.log file (JSON lines format)."""
    log_path = _get_log_path()
    logs = []
    
    if not log_path.exists():
        return logs
    
    try:
        with open(log_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Parse timestamp
                    timestamp = data.get("timestamp")
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    elif timestamp is None:
                        timestamp = datetime.utcnow()
                    
                    # Parse level
                    level_str = data.get("level", "info").upper()
                    try:
                        level = LogLevel(level_str.lower())
                    except ValueError:
                        level = LogLevel.INFO
                    
                    logs.append(LogEntry(
                        timestamp=timestamp,
                        level=level,
                        message=data.get("message", ""),
                        source=data.get("source", "unknown"),
                        job_id=data.get("job_id"),
                        asset_id=data.get("asset_id"),
                        metadata=data.get("metadata")
                    ))
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    # Skip malformed lines
                    continue
    except IOError as e:
        pass
    
    return logs


def _write_log(entry: LogEntry):
    """Write a log entry to the pipeline.log file."""
    log_path = _get_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    log_data = {
        "timestamp": entry.timestamp.isoformat(),
        "level": entry.level.value,
        "message": entry.message,
        "source": entry.source,
    }
    
    if entry.job_id:
        log_data["job_id"] = entry.job_id
    if entry.asset_id:
        log_data["asset_id"] = entry.asset_id
    if entry.metadata:
        log_data["metadata"] = entry.metadata
    
    with open(log_path, "a") as f:
        f.write(json.dumps(log_data) + "\n")


@router.post("/write")
async def write_log(request: LogWriteRequest):
    """
    Write a log entry to the pipeline log.
    
    This endpoint is called by the agent and scrapers to log events.
    """
    entry = LogEntry(
        timestamp=datetime.utcnow(),
        level=request.level,
        message=request.message,
        source=request.source,
        job_id=request.job_id,
        asset_id=request.asset_id,
        metadata=request.metadata
    )
    
    _write_log(entry)
    
    return {"status": "ok", "timestamp": entry.timestamp.isoformat()}


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
    
    Reads from local pipeline.log file in JSON lines format.
    """
    logs = _load_logs()
    
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
    logs = _load_logs()
    logs = [l for l in logs if l.level in [LogLevel.ERROR, LogLevel.CRITICAL]]
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
    logs = _load_logs()
    sources = set(l.source for l in logs if l.source)
    return {"sources": sorted(sources)}


@router.get("/stats")
async def get_log_stats():
    """Get log statistics."""
    logs = _load_logs()
    level_counts = {}
    source_counts = {}
    
    for log in logs:
        level_counts[log.level.value] = level_counts.get(log.level.value, 0) + 1
        if log.source:
            source_counts[log.source] = source_counts.get(log.source, 0) + 1
    
    return {
        "total_logs": len(logs),
        "by_level": level_counts,
        "by_source": source_counts
    }


@router.delete("/clear")
async def clear_logs():
    """Clear all logs (development only)."""
    settings = get_settings()
    if settings.environment not in ["development", "local"]:
        raise HTTPException(status_code=403, detail="Log clearing only allowed in development")
    
    log_path = _get_log_path()
    if log_path.exists():
        log_path.write_text("")
    
    return {"status": "ok", "message": "Logs cleared"}
