"""
Screenshot Saver Service

Saves periodic screenshots during scraping for job replay functionality.
Screenshots are stored with metadata for later playback.
"""

import base64
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ScreenshotSaver:
    """Saves periodic screenshots for job replay."""
    
    def __init__(self, base_path: str = "data/screenshots"):
        """
        Initialize the screenshot saver.
        
        Args:
            base_path: Base directory for storing screenshots
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"ScreenshotSaver initialized with base path: {self.base_path}")
    
    async def save(
        self,
        job_id: str,
        frame_data: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a screenshot with timestamp.
        
        Args:
            job_id: The job ID to associate the screenshot with
            frame_data: Base64-encoded image data
            metadata: Optional metadata (url, action, etc.)
            
        Returns:
            The filename of the saved screenshot
        """
        timestamp = datetime.utcnow()
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        
        job_dir = self.base_path / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        
        # Save image
        image_path = job_dir / filename
        try:
            image_bytes = base64.b64decode(frame_data)
            image_path.write_bytes(image_bytes)
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            raise
        
        # Save metadata
        meta_path = job_dir / f"{filename}.json"
        meta_content = {
            "timestamp": timestamp.isoformat(),
            "filename": filename,
            "job_id": job_id,
        }
        if metadata:
            meta_content["url"] = metadata.get("url")
            meta_content["action"] = metadata.get("action")
            meta_content["step"] = metadata.get("step")
        
        meta_path.write_text(json.dumps(meta_content, indent=2))
        
        logger.debug(f"Saved screenshot: {filename} for job {job_id}")
        return filename
    
    def get_job_screenshots(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get all screenshots for a job, sorted by timestamp.
        
        Args:
            job_id: The job ID to get screenshots for
            
        Returns:
            List of screenshot metadata dicts with URLs
        """
        job_dir = self.base_path / job_id
        if not job_dir.exists():
            return []
        
        screenshots = []
        for img_path in sorted(job_dir.glob("*.jpg")):
            meta_path = img_path.parent / f"{img_path.name}.json"
            
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text())
                except json.JSONDecodeError:
                    meta = {}
            else:
                meta = {}
            
            screenshots.append({
                "filename": img_path.name,
                "url": f"/api/v1/screenshots/{job_id}/{img_path.name}",
                "timestamp": meta.get("timestamp"),
                "page_url": meta.get("url"),
                "action": meta.get("action"),
                "step": meta.get("step"),
            })
        
        return screenshots
    
    def get_screenshot_path(self, job_id: str, filename: str) -> Optional[Path]:
        """
        Get the file path for a specific screenshot.
        
        Args:
            job_id: The job ID
            filename: The screenshot filename
            
        Returns:
            Path to the screenshot file, or None if not found
        """
        path = self.base_path / job_id / filename
        if path.exists() and path.is_file():
            return path
        return None
    
    def get_job_screenshot_count(self, job_id: str) -> int:
        """Get the number of screenshots for a job."""
        job_dir = self.base_path / job_id
        if not job_dir.exists():
            return 0
        return len(list(job_dir.glob("*.jpg")))
    
    def job_has_screenshots(self, job_id: str) -> bool:
        """Check if a job has any screenshots."""
        return self.get_job_screenshot_count(job_id) > 0
    
    def delete_job_screenshots(self, job_id: str) -> bool:
        """
        Delete all screenshots for a job.
        
        Args:
            job_id: The job ID
            
        Returns:
            True if deleted successfully
        """
        job_dir = self.base_path / job_id
        if not job_dir.exists():
            return True
        
        try:
            import shutil
            shutil.rmtree(job_dir)
            logger.info(f"Deleted screenshots for job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete screenshots for job {job_id}: {e}")
            return False
    
    def get_total_storage_bytes(self) -> int:
        """Get total storage used by all screenshots in bytes."""
        total = 0
        for path in self.base_path.rglob("*.jpg"):
            total += path.stat().st_size
        return total
    
    def get_all_jobs_with_screenshots(self) -> List[str]:
        """Get list of all job IDs that have screenshots."""
        jobs = []
        if self.base_path.exists():
            for job_dir in self.base_path.iterdir():
                if job_dir.is_dir() and any(job_dir.glob("*.jpg")):
                    jobs.append(job_dir.name)
        return sorted(jobs)
