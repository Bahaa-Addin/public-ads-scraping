"""
Metrics API Router

Endpoints for pipeline metrics and analytics.
"""

from typing import List, Optional
from fastapi import APIRouter, Query, Depends

from ..models import (
    DashboardMetrics, PipelineMetrics, QueueMetrics, SystemMetrics,
    IndustryDistribution, TimeSeriesData
)
from ..services.metrics_service import MetricsService, get_metrics_service

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/dashboard", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get all dashboard metrics in a single request."""
    return await metrics_service.get_dashboard_metrics()


@router.get("/pipeline", response_model=PipelineMetrics)
async def get_pipeline_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get pipeline-level metrics."""
    return await metrics_service.get_pipeline_metrics()


@router.get("/queue", response_model=QueueMetrics)
async def get_queue_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get job queue metrics."""
    return await metrics_service.job_service.get_queue_metrics()


@router.get("/system", response_model=SystemMetrics)
async def get_system_metrics(
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get system-level metrics."""
    return await metrics_service.get_system_metrics()


@router.get("/industry-distribution", response_model=List[IndustryDistribution])
async def get_industry_distribution(
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get industry classification distribution."""
    return await metrics_service.get_industry_distribution()


@router.get("/time-series/{metric_name}", response_model=TimeSeriesData)
async def get_time_series(
    metric_name: str,
    hours: int = Query(default=24, ge=1, le=168),
    interval_minutes: int = Query(default=60, ge=5, le=360),
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """
    Get time series data for a specific metric.
    
    Available metrics:
    - assets_scraped
    - features_extracted
    - prompts_generated
    - error_rate
    - queue_length
    - throughput
    """
    return await metrics_service.get_time_series_metrics(
        metric_name=metric_name,
        hours=hours,
        interval_minutes=interval_minutes
    )


@router.get("/time-series", response_model=List[TimeSeriesData])
async def get_multi_time_series(
    metrics: List[str] = Query(
        default=["assets_scraped", "features_extracted", "prompts_generated"]
    ),
    hours: int = Query(default=24, ge=1, le=168),
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get multiple time series for comparison charts."""
    return await metrics_service.get_multi_series_metrics(
        metric_names=metrics,
        hours=hours
    )


@router.get("/cta-distribution")
async def get_cta_distribution(
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get CTA type distribution."""
    return await metrics_service.get_cta_distribution()


@router.get("/quality-distribution")
async def get_quality_distribution(
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get quality score distribution in buckets."""
    return await metrics_service.get_quality_distribution()


@router.get("/summary")
async def get_metrics_summary(
    metrics_service: MetricsService = Depends(get_metrics_service)
):
    """Get a quick summary of key metrics for dashboard cards."""
    pipeline = await metrics_service.get_pipeline_metrics()
    queue = await metrics_service.job_service.get_queue_metrics()
    system = await metrics_service.get_system_metrics()
    
    return {
        "total_assets": pipeline.assets_scraped,
        "features_extracted": pipeline.features_extracted,
        "prompts_generated": pipeline.prompts_generated,
        "pending_jobs": queue.pending_jobs,
        "in_progress_jobs": queue.in_progress_jobs,
        "failed_jobs": queue.failed_jobs,
        "error_rate": system.error_rate_percent,
        "throughput": system.scraper_throughput_per_minute,
        "queue_length": system.pubsub_queue_length
    }

