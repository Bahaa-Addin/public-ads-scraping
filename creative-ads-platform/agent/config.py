"""
Configuration Management for Creative Ads Platform

Handles environment variables, secrets, and runtime configuration
for all platform components.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import json


class ScraperSource(Enum):
    """Supported scraper sources."""
    META_AD_LIBRARY = "meta_ad_library"
    GOOGLE_ADS_TRANSPARENCY = "google_ads_transparency"
    INTERNET_ARCHIVE = "internet_archive"
    WIKIMEDIA_COMMONS = "wikimedia_commons"


class IndustryCategory(Enum):
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


@dataclass
class ScraperConfig:
    """Configuration for individual scrapers."""
    source: ScraperSource
    enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    timeout_seconds: int = 30
    batch_size: int = 10
    custom_headers: Dict[str, str] = field(default_factory=dict)
    proxy_url: Optional[str] = None


@dataclass
class VertexAIConfig:
    """Configuration for Vertex AI integration."""
    project_id: str
    location: str = "us-central1"
    model_name: str = "gemini-1.5-pro"
    endpoint_id: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7


@dataclass
class Config:
    """Main platform configuration."""
    # GCP Settings
    gcp_project_id: str
    gcp_region: str = "us-central1"
    gcp_service_account: Optional[str] = None
    
    # Firestore Settings
    firestore_collection_prefix: str = "creative_ads"
    firestore_database_id: str = "(default)"
    
    # Cloud Storage Settings
    storage_bucket_raw: str = ""
    storage_bucket_processed: str = ""
    
    # Pub/Sub Settings
    pubsub_topic: str = "creative-ads-jobs"
    pubsub_subscription: str = "creative-ads-jobs-sub"
    pubsub_dlq_topic: str = "creative-ads-jobs-dlq"
    
    # BigQuery Settings (optional)
    bigquery_dataset: str = "creative_ads_analytics"
    bigquery_enabled: bool = False
    
    # Vertex AI Settings
    vertex_ai: Optional[VertexAIConfig] = None
    
    # Scraper Configurations
    scrapers: Dict[ScraperSource, ScraperConfig] = field(default_factory=dict)
    
    # Agent Settings
    max_concurrent_jobs: int = 10
    job_timeout_seconds: int = 300
    health_check_interval_seconds: int = 60
    
    # Feature Extraction Settings
    feature_extraction_batch_size: int = 50
    
    # Monitoring Settings
    enable_cloud_monitoring: bool = True
    enable_cloud_logging: bool = True
    log_level: str = "INFO"
    
    # Rate Limiting
    global_rate_limit_requests_per_minute: int = 1000
    
    @classmethod
    def from_environment(cls) -> "Config":
        """Create configuration from environment variables."""
        gcp_project_id = os.environ.get("GCP_PROJECT_ID", "")
        
        if not gcp_project_id:
            raise ValueError("GCP_PROJECT_ID environment variable is required")
        
        config = cls(
            gcp_project_id=gcp_project_id,
            gcp_region=os.environ.get("GCP_REGION", "us-central1"),
            gcp_service_account=os.environ.get("GCP_SERVICE_ACCOUNT"),
            firestore_collection_prefix=os.environ.get(
                "FIRESTORE_COLLECTION_PREFIX", "creative_ads"
            ),
            storage_bucket_raw=os.environ.get(
                "STORAGE_BUCKET_RAW", f"{gcp_project_id}-raw-assets"
            ),
            storage_bucket_processed=os.environ.get(
                "STORAGE_BUCKET_PROCESSED", f"{gcp_project_id}-processed-assets"
            ),
            pubsub_topic=os.environ.get("PUBSUB_TOPIC", "creative-ads-jobs"),
            pubsub_subscription=os.environ.get(
                "PUBSUB_SUBSCRIPTION", "creative-ads-jobs-sub"
            ),
            bigquery_enabled=os.environ.get("BIGQUERY_ENABLED", "false").lower() == "true",
            max_concurrent_jobs=int(os.environ.get("MAX_CONCURRENT_JOBS", "10")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )
        
        # Configure Vertex AI
        config.vertex_ai = VertexAIConfig(
            project_id=gcp_project_id,
            location=os.environ.get("VERTEX_AI_LOCATION", "us-central1"),
            model_name=os.environ.get("VERTEX_AI_MODEL", "gemini-1.5-pro"),
            endpoint_id=os.environ.get("VERTEX_AI_ENDPOINT_ID"),
        )
        
        # Configure default scrapers
        config.scrapers = cls._default_scraper_configs()
        
        return config
    
    @classmethod
    def from_json_file(cls, filepath: str) -> "Config":
        """Load configuration from a JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: dict) -> "Config":
        """Create configuration from a dictionary."""
        # Extract Vertex AI config if present
        vertex_ai_data = data.pop('vertex_ai', None)
        vertex_ai = VertexAIConfig(**vertex_ai_data) if vertex_ai_data else None
        
        # Extract scraper configs
        scrapers_data = data.pop('scrapers', {})
        scrapers = {}
        for source_name, scraper_data in scrapers_data.items():
            source = ScraperSource(source_name)
            scrapers[source] = ScraperConfig(source=source, **scraper_data)
        
        return cls(
            **data,
            vertex_ai=vertex_ai,
            scrapers=scrapers or cls._default_scraper_configs()
        )
    
    @staticmethod
    def _default_scraper_configs() -> Dict[ScraperSource, ScraperConfig]:
        """Get default scraper configurations."""
        return {
            ScraperSource.META_AD_LIBRARY: ScraperConfig(
                source=ScraperSource.META_AD_LIBRARY,
                rate_limit_requests_per_minute=30,
                max_retries=3,
                batch_size=25,
            ),
            ScraperSource.GOOGLE_ADS_TRANSPARENCY: ScraperConfig(
                source=ScraperSource.GOOGLE_ADS_TRANSPARENCY,
                rate_limit_requests_per_minute=60,
                max_retries=3,
                batch_size=20,
            ),
            ScraperSource.INTERNET_ARCHIVE: ScraperConfig(
                source=ScraperSource.INTERNET_ARCHIVE,
                rate_limit_requests_per_minute=120,
                max_retries=5,
                batch_size=50,
            ),
            ScraperSource.WIKIMEDIA_COMMONS: ScraperConfig(
                source=ScraperSource.WIKIMEDIA_COMMONS,
                rate_limit_requests_per_minute=100,
                max_retries=3,
                batch_size=50,
            ),
        }
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            "gcp_project_id": self.gcp_project_id,
            "gcp_region": self.gcp_region,
            "gcp_service_account": self.gcp_service_account,
            "firestore_collection_prefix": self.firestore_collection_prefix,
            "storage_bucket_raw": self.storage_bucket_raw,
            "storage_bucket_processed": self.storage_bucket_processed,
            "pubsub_topic": self.pubsub_topic,
            "pubsub_subscription": self.pubsub_subscription,
            "bigquery_enabled": self.bigquery_enabled,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "log_level": self.log_level,
            "vertex_ai": {
                "project_id": self.vertex_ai.project_id,
                "location": self.vertex_ai.location,
                "model_name": self.vertex_ai.model_name,
            } if self.vertex_ai else None,
        }

