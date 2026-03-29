"""
Metrics Service for Dashboard

Provides aggregated metrics and analytics data.
In local mode, reads from local JSON files instead of Cloud Monitoring.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import lru_cache

from ..config import get_settings, Settings
from ..models import (
    PipelineMetrics, QueueMetrics, SystemMetrics, DashboardMetrics,
    IndustryDistribution, IndustryCategory, TimeSeriesData, TimeSeriesDataPoint,
    ScraperStatus, ScraperMetrics, ScraperSource
)
from .firestore_service import FirestoreService, get_firestore_service
from .job_service import JobService, get_job_service

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for metrics and analytics."""
    
    def __init__(
        self, 
        settings: Settings, 
        firestore: FirestoreService,
        job_service: JobService
    ):
        self.settings = settings
        self.firestore = firestore
        self.job_service = job_service
        self._monitoring_client = None
    
    def _get_data_path(self, filename: str) -> Path:
        """Get the full path to a data file."""
        data_dir = self.settings.data_dir
        if not os.path.isabs(data_dir):
            backend_dir = Path(__file__).parent.parent.parent
            data_dir = backend_dir / data_dir
        return Path(data_dir) / filename
    
    def _load_json_file(self, filename: str, default: Any = None) -> Any:
        """Load a JSON file from the data directory."""
        path = self._get_data_path(filename)
        if path.exists():
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load {path}: {e}")
        return default if default is not None else {}
    
    def _save_json_file(self, filename: str, data: Any):
        """Save data to a JSON file in the data directory."""
        path = self._get_data_path(filename)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save {path}: {e}")
    
    async def get_dashboard_metrics(self) -> DashboardMetrics:
        """Get all dashboard metrics."""
        pipeline = await self.get_pipeline_metrics()
        queue = await self.job_service.get_queue_metrics()
        system = await self.get_system_metrics()
        
        return DashboardMetrics(
            pipeline=pipeline,
            queue=queue,
            system=system,
            timestamp=datetime.utcnow()
        )
    
    async def get_pipeline_metrics(self) -> PipelineMetrics:
        """Get pipeline-level metrics calculated from actual data."""
        industry_dist = await self.firestore.get_industry_distribution()
        source_dist = await self.firestore.get_source_distribution()
        
        total_assets = sum(industry_dist.values())
        
        # Calculate from actual asset data
        if total_assets > 0:
            assets, _ = await self.firestore.get_assets(page_size=1000)
            features_extracted = sum(1 for a in assets if a.features)
            prompts_generated = sum(1 for a in assets if a.reverse_prompt)
            errors = sum(1 for a in assets if not a.features and not a.reverse_prompt)
        else:
            features_extracted = 0
            prompts_generated = 0
            errors = 0
        
        return PipelineMetrics(
            assets_scraped=total_assets,
            features_extracted=features_extracted,
            prompts_generated=prompts_generated,
            assets_stored=total_assets,
            errors=errors,
            by_source=source_dist,
            by_industry=industry_dist
        )
    
    async def get_system_metrics(self) -> SystemMetrics:
        """Get system-level metrics from local files or Cloud Monitoring."""
        # Load from local file
        metrics_data = self._load_json_file("metrics/system_metrics.json", {
            "throughput": 0,
            "latency": 0,
            "error_rate": 0,
            "uptime": 0
        })
        
        return SystemMetrics(
            scraper_throughput_per_minute=metrics_data.get("throughput", 0),
            feature_extraction_latency_ms=metrics_data.get("feature_extraction_latency", 0),
            prompt_generation_latency_ms=metrics_data.get("prompt_generation_latency", 0),
            pubsub_queue_length=metrics_data.get("queue_length", 0),
            cloud_run_utilization=metrics_data.get("utilization", {
                "agent": 0,
                "scraper": 0,
                "dashboard": 0
            }),
            error_rate_percent=metrics_data.get("error_rate", 0)
        )
    
    async def update_system_metrics(self, updates: Dict[str, Any]):
        """Update system metrics (called by agent/scrapers)."""
        current = self._load_json_file("metrics/system_metrics.json", {})
        current.update(updates)
        current["last_updated"] = datetime.utcnow().isoformat()
        self._save_json_file("metrics/system_metrics.json", current)
    
    async def get_industry_distribution(self) -> List[IndustryDistribution]:
        """Get industry distribution with percentages."""
        dist = await self.firestore.get_industry_distribution()
        total = sum(dist.values())
        
        if total == 0:
            return []
        
        return [
            IndustryDistribution(
                industry=IndustryCategory(industry),
                count=count,
                percentage=round((count / total) * 100, 2)
            )
            for industry, count in sorted(
                dist.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
            if count > 0
        ]
    
    async def get_scraper_statuses(self) -> List[ScraperStatus]:
        """Get status of all scrapers from local file."""
        statuses_data = self._load_json_file("metrics/scraper_status.json", [])
        
        if not statuses_data:
            # Return default statuses for all sources with no activity
            source_dist = await self.firestore.get_source_distribution()
            return [
                ScraperStatus(
                    source=source,
                    enabled=True,
                    running=False,
                    last_run=None,
                    items_scraped=source_dist.get(source.value, 0),
                    success_rate=0,
                    error_count=0,
                    last_error=None
                )
                for source in ScraperSource
            ]
        
        statuses = []
        for status in statuses_data:
            try:
                source = ScraperSource(status.get("source", "meta_ad_library"))
                statuses.append(ScraperStatus(
                    source=source,
                    enabled=status.get("enabled", True),
                    running=status.get("running", False),
                    last_run=datetime.fromisoformat(status["last_run"]) if status.get("last_run") else None,
                    items_scraped=status.get("items_scraped", 0),
                    success_rate=status.get("success_rate", 0),
                    error_count=status.get("error_count", 0),
                    last_error=status.get("last_error")
                ))
            except (ValueError, KeyError) as e:
                logger.warning(f"Failed to parse scraper status: {e}")
        
        return statuses
    
    async def update_scraper_status(self, source: ScraperSource, updates: Dict[str, Any]):
        """Update scraper status (called by scrapers)."""
        statuses = self._load_json_file("metrics/scraper_status.json", [])
        
        # Find or create status for this source
        found = False
        for status in statuses:
            if status.get("source") == source.value:
                status.update(updates)
                status["source"] = source.value
                found = True
                break
        
        if not found:
            updates["source"] = source.value
            statuses.append(updates)
        
        self._save_json_file("metrics/scraper_status.json", statuses)
    
    async def get_scraper_metrics(self) -> List[ScraperMetrics]:
        """Get detailed metrics per scraper from actual data."""
        metrics = []
        source_dist = await self.firestore.get_source_distribution()
        scraper_statuses = await self.get_scraper_statuses()
        
        status_map = {s.source.value: s for s in scraper_statuses}
        
        for source in ScraperSource:
            total = source_dist.get(source.value, 0)
            status = status_map.get(source.value)
            
            if status:
                failed = status.error_count
                success_rate = status.success_rate
            else:
                failed = 0
                success_rate = 0
            
            metrics.append(ScraperMetrics(
                source=source,
                total_items=total,
                successful_items=total - failed if total > failed else 0,
                failed_items=failed,
                avg_scrape_time_ms=0,  # Will be populated by agent
                rate_limit_hits=0       # Will be populated by agent
            ))
        
        return metrics
    
    async def get_time_series_metrics(
        self,
        metric_name: str,
        hours: int = 24,
        interval_minutes: int = 60
    ) -> TimeSeriesData:
        """Get time series data for a metric from local file."""
        time_series = self._load_json_file("metrics/time_series.json", {})
        
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=hours)
        
        # Filter data points for this metric within the time range
        data_points = []
        
        # Handle both formats:
        # 1. Dict format: {"metric_name": [{"timestamp": "...", "value": 0}]}
        # 2. Array format: [{"metric": "metric_name", "timestamp": "...", "value": 0}]
        if isinstance(time_series, dict):
            # New dict format from Agent's DataService
            metric_data = time_series.get(metric_name, [])
            for entry in metric_data:
                try:
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    if timestamp >= cutoff:
                        data_points.append(TimeSeriesDataPoint(
                            timestamp=timestamp,
                            value=entry.get("value", 0)
                        ))
                except (ValueError, KeyError):
                    continue
        else:
            # Legacy array format
            for entry in time_series:
                if entry.get("metric") != metric_name:
                    continue
                
                try:
                    timestamp = datetime.fromisoformat(entry["timestamp"])
                    if timestamp >= cutoff:
                        data_points.append(TimeSeriesDataPoint(
                            timestamp=timestamp,
                            value=entry.get("value", 0)
                        ))
                except (ValueError, KeyError):
                    continue
        
        # Sort by timestamp
        data_points.sort(key=lambda x: x.timestamp)
        
        colors = {
            "assets_scraped": "#3B82F6",
            "features_extracted": "#10B981",
            "prompts_generated": "#8B5CF6",
            "error_rate": "#EF4444",
            "queue_length": "#F59E0B",
            "throughput": "#06B6D4"
        }
        
        return TimeSeriesData(
            name=metric_name,
            data=data_points,
            color=colors.get(metric_name, "#6B7280")
        )
    
    async def add_time_series_point(self, metric_name: str, value: float):
        """Add a data point to time series (called by agent/scrapers)."""
        time_series = self._load_json_file("metrics/time_series.json", [])
        
        time_series.append({
            "metric": metric_name,
            "timestamp": datetime.utcnow().isoformat(),
            "value": value
        })
        
        # Keep only last 7 days of data
        cutoff = datetime.utcnow() - timedelta(days=7)
        time_series = [
            entry for entry in time_series
            if datetime.fromisoformat(entry["timestamp"]) >= cutoff
        ]
        
        self._save_json_file("metrics/time_series.json", time_series)
    
    async def get_multi_series_metrics(
        self,
        metric_names: List[str],
        hours: int = 24
    ) -> List[TimeSeriesData]:
        """Get multiple time series for comparison charts."""
        return [
            await self.get_time_series_metrics(name, hours)
            for name in metric_names
        ]
    
    async def get_cta_distribution(self) -> Dict[str, int]:
        """Get CTA type distribution."""
        return await self.firestore.get_cta_distribution()
    
    async def get_quality_distribution(self) -> Dict[str, int]:
        """Get quality score distribution from Firestore service."""
        return await self.firestore.get_quality_distribution()


@lru_cache()
def get_metrics_service() -> MetricsService:
    """Get cached MetricsService instance."""
    return MetricsService(
        get_settings(), 
        get_firestore_service(),
        get_job_service()
    )
