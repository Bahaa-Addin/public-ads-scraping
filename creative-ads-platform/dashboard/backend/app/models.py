"""
Pydantic Models for Dashboard API

Defines request/response schemas for all API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Types of jobs in the pipeline."""
    SCRAPE = "scrape"
    EXTRACT_FEATURES = "extract_features"
    GENERATE_PROMPT = "generate_prompt"
    CLASSIFY_INDUSTRY = "classify_industry"
    STORE_ASSET = "store_asset"
    BATCH_PROCESS = "batch_process"


class ScraperSource(str, Enum):
    """Supported scraper sources."""
    META_AD_LIBRARY = "meta_ad_library"
    GOOGLE_ADS_TRANSPARENCY = "google_ads_transparency"
    INTERNET_ARCHIVE = "internet_archive"
    WIKIMEDIA_COMMONS = "wikimedia_commons"


class IndustryCategory(str, Enum):
    """Industry classification categories."""
    FINANCE = "finance"
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    ENTERTAINMENT = "entertainment"
    FOOD_BEVERAGE = "food_beverage"
    TRAVEL = "travel"
    AUTOMOTIVE = "automotive"
    REAL_ESTATE = "real_estate"
    FASHION = "fashion"
    TECHNOLOGY = "technology"
    OTHER = "other"


class LogLevel(str, Enum):
    """Log severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# =============================================================================
# Base Models
# =============================================================================

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# =============================================================================
# Job Models
# =============================================================================

class JobBase(BaseModel):
    """Base job model."""
    job_type: JobType
    source: Optional[ScraperSource] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=0, ge=0, le=10)


class JobCreate(JobBase):
    """Create job request."""
    max_items: int = Field(default=100, ge=1, le=1000)
    query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


class Job(JobBase, TimestampMixin):
    """Full job model."""
    id: str
    status: JobStatus = JobStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    assets_processed: int = 0
    
    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Response for job listing."""
    jobs: List[Job]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False


class JobControlRequest(BaseModel):
    """Request to control a job."""
    action: str = Field(..., pattern="^(start|stop|pause|resume|retry|cancel)$")
    job_ids: List[str]


class JobControlResponse(BaseModel):
    """Response for job control actions."""
    success: bool
    affected_jobs: List[str]
    message: str


# =============================================================================
# Asset Models
# =============================================================================

class ColorInfo(BaseModel):
    """Color information."""
    hex: str
    percentage: float = 0.0


class CTAInfo(BaseModel):
    """CTA information."""
    detected: bool = False
    type: Optional[str] = None
    text: Optional[str] = None
    prominence: float = 0.0


class ExtractedFeatures(BaseModel):
    """Extracted visual features."""
    layout_type: Optional[str] = None
    focal_point: Optional[str] = None
    visual_complexity: Optional[str] = None
    tone: Optional[str] = None
    dominant_colors: List[ColorInfo] = Field(default_factory=list)
    cta: Optional[CTAInfo] = None
    quality_score: Optional[float] = None
    has_logo: bool = False
    has_human_face: bool = False
    has_product: bool = False


class AssetBase(BaseModel):
    """Base asset model."""
    source: ScraperSource
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    asset_type: str = "image"


class Asset(AssetBase, TimestampMixin):
    """Full asset model."""
    id: str
    advertiser_name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    
    # Features
    features: Optional[ExtractedFeatures] = None
    
    # Classification
    industry: Optional[IndustryCategory] = None
    industry_tags: Optional[Dict[str, Any]] = None
    
    # Prompts
    reverse_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    prompt_metadata: Optional[Dict[str, Any]] = None
    
    # Storage
    raw_asset_path: Optional[str] = None
    processed_asset_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    
    # Processing status
    processed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """Response for asset listing."""
    assets: List[Asset]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False


class AssetFilterParams(BaseModel):
    """Parameters for filtering assets."""
    industry: Optional[IndustryCategory] = None
    source: Optional[ScraperSource] = None
    cta_type: Optional[str] = None
    focal_point: Optional[str] = None
    tone: Optional[str] = None
    has_prompt: Optional[bool] = None
    min_quality: Optional[float] = None
    search: Optional[str] = None


class AssetReprocessRequest(BaseModel):
    """Request to reprocess assets."""
    asset_ids: List[str]
    stages: List[str] = Field(
        default=["extract_features", "generate_prompt"],
        description="Pipeline stages to run"
    )


# =============================================================================
# Scraper Models
# =============================================================================

class ScraperStatus(BaseModel):
    """Status of a scraper."""
    source: ScraperSource
    enabled: bool = True
    running: bool = False
    last_run: Optional[datetime] = None
    items_scraped: int = 0
    success_rate: float = 0.0
    error_count: int = 0
    last_error: Optional[str] = None


class ScraperMetrics(BaseModel):
    """Metrics for scrapers."""
    source: ScraperSource
    total_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    avg_scrape_time_ms: float = 0.0
    rate_limit_hits: int = 0


class ScraperTriggerRequest(BaseModel):
    """Request to trigger scraping."""
    sources: List[ScraperSource]
    query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    max_items_per_source: int = Field(default=100, ge=1, le=1000)
    industries: Optional[List[IndustryCategory]] = None


class ScraperTriggerResponse(BaseModel):
    """Response for scraper trigger."""
    triggered: bool
    job_ids: List[str]
    message: str


# =============================================================================
# Metrics Models
# =============================================================================

class PipelineMetrics(BaseModel):
    """Pipeline-level metrics."""
    assets_scraped: int = 0
    features_extracted: int = 0
    prompts_generated: int = 0
    assets_stored: int = 0
    errors: int = 0
    
    # Per-source
    by_source: Dict[str, int] = Field(default_factory=dict)
    
    # Per-industry
    by_industry: Dict[str, int] = Field(default_factory=dict)


class QueueMetrics(BaseModel):
    """Job queue metrics."""
    total_jobs: int = 0
    pending_jobs: int = 0
    in_progress_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    dead_letter_jobs: int = 0
    avg_processing_time_seconds: float = 0.0
    jobs_per_minute: float = 0.0


class SystemMetrics(BaseModel):
    """System-level metrics."""
    scraper_throughput_per_minute: float = 0.0
    feature_extraction_latency_ms: float = 0.0
    prompt_generation_latency_ms: float = 0.0
    pubsub_queue_length: int = 0
    cloud_run_utilization: Dict[str, float] = Field(default_factory=dict)
    error_rate_percent: float = 0.0


class DashboardMetrics(BaseModel):
    """Combined dashboard metrics."""
    pipeline: PipelineMetrics
    queue: QueueMetrics
    system: SystemMetrics
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IndustryDistribution(BaseModel):
    """Industry classification distribution."""
    industry: IndustryCategory
    count: int
    percentage: float


class TimeSeriesDataPoint(BaseModel):
    """Single data point for time series."""
    timestamp: datetime
    value: float
    label: Optional[str] = None


class TimeSeriesData(BaseModel):
    """Time series data for charts."""
    name: str
    data: List[TimeSeriesDataPoint]
    color: Optional[str] = None


# =============================================================================
# Log Models
# =============================================================================

class LogEntry(BaseModel):
    """Single log entry."""
    timestamp: datetime
    level: LogLevel
    message: str
    source: Optional[str] = None
    job_id: Optional[str] = None
    asset_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class LogSearchParams(BaseModel):
    """Parameters for log search."""
    job_id: Optional[str] = None
    asset_id: Optional[str] = None
    level: Optional[LogLevel] = None
    source: Optional[str] = None
    search: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class LogSearchResponse(BaseModel):
    """Response for log search."""
    logs: List[LogEntry]
    total: int
    has_more: bool = False


# =============================================================================
# Notification Models
# =============================================================================

class NotificationSeverity(str, Enum):
    """Notification severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Notification(BaseModel):
    """Dashboard notification."""
    id: str
    severity: NotificationSeverity
    title: str
    message: str
    timestamp: datetime
    read: bool = False
    action_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# =============================================================================
# Export Models
# =============================================================================

class ExportFormat(str, Enum):
    """Export file formats."""
    JSON = "json"
    CSV = "csv"
    EXCEL = "xlsx"


class ExportRequest(BaseModel):
    """Request to export data."""
    asset_ids: Optional[List[str]] = None
    filters: Optional[AssetFilterParams] = None
    format: ExportFormat = ExportFormat.JSON
    include_features: bool = True
    include_prompts: bool = True


class ExportResponse(BaseModel):
    """Response for export request."""
    download_url: str
    expires_at: datetime
    file_size_bytes: int
    record_count: int


# =============================================================================
# Health Models
# =============================================================================

class ServiceHealth(BaseModel):
    """Health status of a service."""
    name: str
    healthy: bool
    latency_ms: Optional[float] = None
    last_check: datetime
    message: Optional[str] = None


class HealthResponse(BaseModel):
    """Overall health response."""
    status: str
    timestamp: datetime
    version: str
    uptime_seconds: float
    services: List[ServiceHealth]

