"""
Data Service - Persistent storage for jobs, assets, and metrics.

This service handles reading and writing to the shared data directory
that both the Agent and Dashboard Backend use.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataService:
    """
    Manages persistent storage for the agent.
    
    Writes to:
    - data/db/jobs.json - Job records
    - data/db/assets.json - Scraped assets
    - data/metrics/scraper_status.json - Scraper metrics
    - data/metrics/system_metrics.json - System metrics
    """
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.jobs_path = self.data_dir / "db" / "jobs.json"
        self.assets_path = self.data_dir / "db" / "assets.json"
        self.scraper_status_path = self.data_dir / "metrics" / "scraper_status.json"
        self.system_metrics_path = self.data_dir / "metrics" / "system_metrics.json"
        self.time_series_path = self.data_dir / "metrics" / "time_series.json"
        
        # Ensure directories exist
        (self.data_dir / "db").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "metrics").mkdir(parents=True, exist_ok=True)
        
        logger.info(f"DataService initialized with data_dir: {self.data_dir}")
    
    # =========================================================================
    # Job Management
    # =========================================================================
    
    def _read_jobs(self) -> List[Dict]:
        """Read all jobs from file."""
        if not self.jobs_path.exists():
            return []
        try:
            with open(self.jobs_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read jobs: {e}")
            return []
    
    def _write_jobs(self, jobs: List[Dict]) -> bool:
        """Write jobs to file."""
        try:
            with open(self.jobs_path, 'w') as f:
                json.dump(jobs, f, indent=2, default=str)
            return True
        except IOError as e:
            logger.error(f"Failed to write jobs: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get a specific job by ID."""
        jobs = self._read_jobs()
        for job in jobs:
            if job.get("id") == job_id:
                return job
        return None
    
    def update_job_status(
        self,
        job_id: str,
        status: str,
        assets_processed: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update job status in the jobs file.
        
        Args:
            job_id: The job ID to update
            status: New status (pending, in_progress, completed, failed)
            assets_processed: Number of assets processed
            error_message: Error message if failed
        """
        jobs = self._read_jobs()
        updated = False
        
        for job in jobs:
            if job.get("id") == job_id:
                job["status"] = status
                job["updated_at"] = datetime.utcnow().isoformat()
                
                if status == "in_progress" and not job.get("started_at"):
                    job["started_at"] = datetime.utcnow().isoformat()
                
                if status in ["completed", "failed"]:
                    job["completed_at"] = datetime.utcnow().isoformat()
                
                if assets_processed is not None:
                    job["assets_processed"] = assets_processed
                
                if error_message:
                    job["error_message"] = error_message
                
                updated = True
                break
        
        if updated:
            self._write_jobs(jobs)
            logger.info(f"Updated job {job_id} status to {status}")
        else:
            logger.warning(f"Job {job_id} not found for status update")
        
        return updated
    
    # =========================================================================
    # Asset Management
    # =========================================================================
    
    def _read_assets(self) -> List[Dict]:
        """Read all assets from file."""
        if not self.assets_path.exists():
            return []
        try:
            with open(self.assets_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read assets: {e}")
            return []
    
    def _write_assets(self, assets: List[Dict]) -> bool:
        """Write assets to file."""
        try:
            with open(self.assets_path, 'w') as f:
                json.dump(assets, f, indent=2, default=str)
            return True
        except IOError as e:
            logger.error(f"Failed to write assets: {e}")
            return False
    
    def save_assets(self, new_assets: List[Dict], source: str) -> int:
        """
        Save new assets to the assets file.
        
        Args:
            new_assets: List of asset dictionaries from scraper
            source: Source name (e.g., 'meta_ad_library')
            
        Returns:
            Number of assets saved
        """
        existing_assets = self._read_assets()
        existing_ids = {a.get("id") for a in existing_assets}
        
        added = 0
        now = datetime.utcnow().isoformat()
        
        for asset in new_assets:
            # Generate ID if not present
            asset_id = asset.get("id") or str(uuid.uuid4())
            
            if asset_id not in existing_ids:
                normalized_asset = {
                    "id": asset_id,
                    "source": source,
                    "source_url": asset.get("url") or asset.get("source_url"),
                    "image_url": asset.get("imageUrl") or asset.get("image_url"),
                    "asset_type": asset.get("type") or asset.get("asset_type", "image"),
                    "advertiser_name": asset.get("advertiserName") or asset.get("advertiser_name"),
                    "title": asset.get("title"),
                    "description": asset.get("description"),
                    "features": asset.get("features"),
                    "industry": asset.get("industry"),
                    "reverse_prompt": asset.get("reverse_prompt"),
                    "negative_prompt": asset.get("negative_prompt"),
                    "created_at": now,
                    "updated_at": now,
                }
                existing_assets.insert(0, normalized_asset)  # Add to beginning
                existing_ids.add(asset_id)
                added += 1
        
        if added > 0:
            self._write_assets(existing_assets)
            logger.info(f"Saved {added} new assets from {source}")
        
        return added
    
    def get_asset_count(self) -> int:
        """Get total number of assets."""
        return len(self._read_assets())
    
    # =========================================================================
    # Scraper Metrics
    # =========================================================================
    
    def _read_scraper_status(self) -> Dict[str, Dict]:
        """Read scraper status from file."""
        if not self.scraper_status_path.exists():
            return {}
        try:
            with open(self.scraper_status_path, 'r') as f:
                data = json.load(f)
                # Convert list to dict if needed
                if isinstance(data, list):
                    return {s["source"]: s for s in data}
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read scraper status: {e}")
            return {}
    
    def _write_scraper_status(self, status: Dict[str, Dict]) -> bool:
        """Write scraper status to file as list."""
        try:
            # Convert dict to list for dashboard compatibility
            status_list = list(status.values())
            with open(self.scraper_status_path, 'w') as f:
                json.dump(status_list, f, indent=2, default=str)
            return True
        except IOError as e:
            logger.error(f"Failed to write scraper status: {e}")
            return False
    
    def update_scraper_status(
        self,
        source: str,
        items_scraped: int,
        success: bool,
        error_message: Optional[str] = None
    ) -> None:
        """
        Update scraper status after a run.
        
        Args:
            source: Scraper source name
            items_scraped: Number of items scraped in this run
            success: Whether the run was successful
            error_message: Error message if failed
        """
        status_dict = self._read_scraper_status()
        
        # Get or create source status
        if source not in status_dict:
            status_dict[source] = {
                "source": source,
                "enabled": True,
                "running": False,
                "items_scraped": 0,
                "success_rate": 0.0,
                "error_count": 0,
                "run_count": 0,
            }
        
        scraper = status_dict[source]
        scraper["running"] = False
        scraper["last_run"] = datetime.utcnow().isoformat()
        scraper["items_scraped"] = scraper.get("items_scraped", 0) + items_scraped
        scraper["run_count"] = scraper.get("run_count", 0) + 1
        
        if success:
            success_count = scraper.get("success_count", 0) + 1
            scraper["success_count"] = success_count
            scraper["success_rate"] = (success_count / scraper["run_count"]) * 100
            scraper.pop("last_error", None)
        else:
            scraper["error_count"] = scraper.get("error_count", 0) + 1
            if error_message:
                scraper["last_error"] = error_message
        
        self._write_scraper_status(status_dict)
        logger.info(f"Updated scraper status for {source}")
    
    def set_scraper_running(self, source: str, running: bool = True) -> None:
        """Set scraper running status."""
        status_dict = self._read_scraper_status()
        
        if source not in status_dict:
            status_dict[source] = {
                "source": source,
                "enabled": True,
                "running": running,
                "items_scraped": 0,
                "success_rate": 0.0,
                "error_count": 0,
                "run_count": 0,
            }
        else:
            status_dict[source]["running"] = running
        
        self._write_scraper_status(status_dict)
    
    # =========================================================================
    # System Metrics
    # =========================================================================
    
    def update_system_metrics(
        self,
        assets_scraped: int = 0,
        features_extracted: int = 0,
        prompts_generated: int = 0
    ) -> None:
        """Update system-wide metrics."""
        try:
            if self.system_metrics_path.exists():
                with open(self.system_metrics_path, 'r') as f:
                    metrics = json.load(f)
            else:
                metrics = {
                    "assets_scraped": 0,
                    "features_extracted": 0,
                    "prompts_generated": 0,
                    "error_rate_percent": 0,
                    "scraper_throughput_per_minute": 0,
                    "feature_extraction_latency_ms": 0,
                }
            
            metrics["assets_scraped"] = metrics.get("assets_scraped", 0) + assets_scraped
            metrics["features_extracted"] = metrics.get("features_extracted", 0) + features_extracted
            metrics["prompts_generated"] = metrics.get("prompts_generated", 0) + prompts_generated
            metrics["last_updated"] = datetime.utcnow().isoformat()
            
            with open(self.system_metrics_path, 'w') as f:
                json.dump(metrics, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")
    
    def add_time_series_point(self, metric_name: str, value: float) -> None:
        """Add a data point to time series."""
        try:
            if self.time_series_path.exists():
                with open(self.time_series_path, 'r') as f:
                    series = json.load(f)
            else:
                series = {}
            
            if metric_name not in series:
                series[metric_name] = []
            
            series[metric_name].append({
                "timestamp": datetime.utcnow().isoformat(),
                "value": value
            })
            
            # Keep last 100 points per metric
            series[metric_name] = series[metric_name][-100:]
            
            with open(self.time_series_path, 'w') as f:
                json.dump(series, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to add time series point: {e}")
    
    # =========================================================================
    # Logging
    # =========================================================================
    
    def write_log(
        self,
        level: str,
        message: str,
        source: str = "agent",
        job_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Write a log entry to the pipeline.log file.
        
        This makes logs visible in the Dashboard's Logs page.
        """
        try:
            log_path = self.data_dir / "logs" / "pipeline.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": level.lower(),
                "message": message,
                "source": source,
            }
            
            if job_id:
                log_entry["job_id"] = job_id
            if metadata:
                log_entry["metadata"] = metadata
            
            with open(log_path, 'a') as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Failed to write log: {e}")


# Singleton instance
_data_service: Optional[DataService] = None


def get_data_service(data_dir: str = "./data") -> DataService:
    """Get or create the DataService singleton."""
    global _data_service
    if _data_service is None:
        _data_service = DataService(data_dir)
    return _data_service
