"""
Screenshots API Router

Endpoints for serving screenshot images for job replay.
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/screenshots", tags=["Screenshots"])


def _get_screenshots_path() -> Path:
    """Get the screenshots directory path."""
    settings = get_settings()
    return Path(settings.data_dir) / "screenshots"


@router.get("/{job_id}/{filename}")
async def get_screenshot(job_id: str, filename: str):
    """
    Serve a screenshot image file.
    
    Returns the JPEG image for display in the replay player.
    """
    # Validate filename to prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    if ".." in job_id or "/" in job_id or "\\" in job_id:
        raise HTTPException(status_code=400, detail="Invalid job ID")
    
    path = _get_screenshots_path() / job_id / filename
    
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Screenshot not found")
    
    return FileResponse(path, media_type="image/jpeg")


@router.get("/storage")
async def get_screenshot_storage():
    """Get total storage used by screenshots."""
    screenshots_path = _get_screenshots_path()
    
    if not screenshots_path.exists():
        return {"bytes": 0, "mb": 0}
    
    total_bytes = 0
    for path in screenshots_path.rglob("*.jpg"):
        try:
            total_bytes += path.stat().st_size
        except OSError:
            pass
    
    return {
        "bytes": total_bytes,
        "mb": round(total_bytes / (1024 * 1024), 2),
    }
