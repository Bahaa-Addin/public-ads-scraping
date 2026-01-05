"""
Metrics Service for Dashboard

Provides aggregated metrics and analytics data.
"""

import logging
import random
from datetime import datetime, timedelta
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
        """Get pipeline-level metrics."""
        industry_dist = await self.firestore.get_industry_distribution()
        source_dist = await self.firestore.get_source_distribution()
        
        total_assets = sum(industry_dist.values())
        
        # Estimate based on mock ratios
        features_extracted = int(total_assets * 0.95)
        prompts_generated = int(total_assets * 0.85)
        
        return PipelineMetrics(
            assets_scraped=total_assets,
            features_extracted=features_extracted,
            prompts_generated=prompts_generated,
            assets_stored=total_assets,
            errors=int(total_assets * 0.02),
            by_source=source_dist,
            by_industry=industry_dist
        )
    
    async def get_system_metrics(self) -> SystemMetrics:
        """Get system-level metrics."""
        # In production, this would query Cloud Monitoring
        # For now, return realistic mock values
        return SystemMetrics(
            scraper_throughput_per_minute=45.5,
            feature_extraction_latency_ms=1250.0,
            prompt_generation_latency_ms=2800.0,
            pubsub_queue_length=15,
            cloud_run_utilization={
                "agent": 0.35,
                "scraper": 0.55,
                "dashboard": 0.20
            },
            error_rate_percent=2.3
        )
    
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
        """Get status of all scrapers."""
        statuses = []
        
        for source in ScraperSource:
            source_dist = await self.firestore.get_source_distribution()
            items = source_dist.get(source.value, 0)
            
            statuses.append(ScraperStatus(
                source=source,
                enabled=True,
                running=random.choice([True, False]),  # Mock
                last_run=datetime.utcnow() - timedelta(minutes=random.randint(5, 120)),
                items_scraped=items,
                success_rate=0.95 + random.random() * 0.04,
                error_count=random.randint(0, 10),
                last_error=None if random.random() > 0.3 else "Rate limit exceeded"
            ))
        
        return statuses
    
    async def get_scraper_metrics(self) -> List[ScraperMetrics]:
        """Get detailed metrics per scraper."""
        metrics = []
        source_dist = await self.firestore.get_source_distribution()
        
        for source in ScraperSource:
            total = source_dist.get(source.value, 0)
            failed = int(total * 0.02)
            
            metrics.append(ScraperMetrics(
                source=source,
                total_items=total,
                successful_items=total - failed,
                failed_items=failed,
                avg_scrape_time_ms=1500 + random.random() * 1000,
                rate_limit_hits=random.randint(0, 5)
            ))
        
        return metrics
    
    async def get_time_series_metrics(
        self,
        metric_name: str,
        hours: int = 24,
        interval_minutes: int = 60
    ) -> TimeSeriesData:
        """Get time series data for a metric."""
        now = datetime.utcnow()
        data_points = []
        
        num_points = (hours * 60) // interval_minutes
        
        for i in range(num_points):
            timestamp = now - timedelta(minutes=i * interval_minutes)
            
            # Generate realistic mock values based on metric name
            if metric_name == "assets_scraped":
                base_value = 50 + random.random() * 30
            elif metric_name == "features_extracted":
                base_value = 45 + random.random() * 25
            elif metric_name == "prompts_generated":
                base_value = 40 + random.random() * 20
            elif metric_name == "error_rate":
                base_value = 1.5 + random.random() * 3
            elif metric_name == "queue_length":
                base_value = 10 + random.random() * 20
            elif metric_name == "throughput":
                base_value = 40 + random.random() * 20
            else:
                base_value = random.random() * 100
            
            # Add some time-of-day variation
            hour = timestamp.hour
            if 9 <= hour <= 17:  # Business hours
                base_value *= 1.3
            elif 0 <= hour <= 6:  # Night hours
                base_value *= 0.6
            
            data_points.append(TimeSeriesDataPoint(
                timestamp=timestamp,
                value=round(base_value, 2)
            ))
        
        # Reverse to get chronological order
        data_points.reverse()
        
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
        """Get quality score distribution in buckets."""
        assets, _ = await self.firestore.get_assets(page_size=1000)
        
        buckets = {
            "0.0-0.5": 0,
            "0.5-0.7": 0,
            "0.7-0.8": 0,
            "0.8-0.9": 0,
            "0.9-1.0": 0
        }
        
        for asset in assets:
            if asset.features and asset.features.quality_score:
                score = asset.features.quality_score
                if score < 0.5:
                    buckets["0.0-0.5"] += 1
                elif score < 0.7:
                    buckets["0.5-0.7"] += 1
                elif score < 0.8:
                    buckets["0.7-0.8"] += 1
                elif score < 0.9:
                    buckets["0.8-0.9"] += 1
                else:
                    buckets["0.9-1.0"] += 1
        
        return buckets


@lru_cache()
def get_metrics_service() -> MetricsService:
    """Get cached MetricsService instance."""
    return MetricsService(
        get_settings(), 
        get_firestore_service(),
        get_job_service()
    )

