"""
Configuration Management for Agentic Ads Platform

Handles environment variables, secrets, and runtime configuration
for all platform components.

MODES:
- MODE=local: All services emulated locally (default)
- MODE=cloud: Full GCP deployment

CRITICAL: Vertex AI is ONLY available in cloud mode.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import json


class Mode(Enum):
    """Platform execution mode."""
    LOCAL = "local"
    CLOUD = "cloud"


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
    """
    Configuration for Vertex AI integration.
    
    CLOUD MODE ONLY - Vertex AI is not available locally.
    """
    project_id: str
    location: str = "us-central1"
    model_name: str = "gemini-1.5-pro"
    endpoint_id: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7


@dataclass
class OllamaConfig:
    """Configuration for local Ollama LLM."""
    host: str = "http://localhost:11434"
    model: str = "llama2"
    enabled: bool = False


@dataclass
class LowRAMConfig:
    """
    Low-RAM safety configuration for local development.
    
    These settings ensure the platform can run on machines with limited resources.
    """
    # Browser settings
    max_browser_instances: int = 1
    browser_headless: bool = True
    
    # Scraping settings
    sequential_scraping: bool = True
    max_concurrent_scrapes: int = 1
    
    # Image processing
    image_only_mode: bool = True  # No video processing
    max_image_dimension: int = 1920
    video_frame_sample_limit: int = 10
    
    # Job settings
    global_job_cap: int = 100
    max_queue_size: int = 1000
    
    # Memory limits
    max_assets_in_memory: int = 50


@dataclass
class Config:
    """
    Main platform configuration.
    
    Supports two modes:
    - LOCAL: Everything runs locally with emulators
    - CLOUD: Full GCP deployment
    """
    # Execution mode
    mode: Mode = Mode.LOCAL
    
    # GCP Settings (used in cloud mode)
    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    gcp_service_account: Optional[str] = None
    
    # Local Settings
    data_dir: str = "./data"
    
    # Firestore Settings
    firestore_collection_prefix: str = "creative_ads"
    firestore_database_id: str = "(default)"
    
    # Cloud Storage Settings (cloud mode)
    storage_bucket_raw: str = ""
    storage_bucket_processed: str = ""
    
    # Pub/Sub Settings (cloud mode)
    pubsub_topic: str = "agentic-ads-jobs"
    pubsub_subscription: str = "agentic-ads-jobs-sub"
    pubsub_dlq_topic: str = "agentic-ads-jobs-dlq"
    
    # BigQuery Settings (optional, cloud mode)
    bigquery_dataset: str = "creative_ads_analytics"
    bigquery_enabled: bool = False
    
    # Vertex AI Settings (CLOUD MODE ONLY)
    vertex_ai: Optional[VertexAIConfig] = None
    
    # Ollama Settings (local mode)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    
    # LLM Mode: "template" (default local) or "ollama" (local) or "vertex" (cloud only)
    llm_mode: str = "template"
    
    # Scraper Configurations
    scrapers: Dict[ScraperSource, ScraperConfig] = field(default_factory=dict)
    
    # Agent Settings
    max_concurrent_jobs: int = 10
    job_timeout_seconds: int = 300
    health_check_interval_seconds: int = 60
    
    # Feature Extraction Settings
    feature_extraction_batch_size: int = 50
    
    # Monitoring Settings
    enable_cloud_monitoring: bool = False  # True only in cloud mode
    enable_cloud_logging: bool = False     # True only in cloud mode
    log_level: str = "INFO"
    
    # Rate Limiting
    global_rate_limit_requests_per_minute: int = 1000
    
    # Low-RAM Safety (always enabled in local mode)
    low_ram: LowRAMConfig = field(default_factory=LowRAMConfig)
    
    # Dashboard settings
    dashboard_port: int = 8080
    api_port: int = 8081
    
    # Node.js Scraper Service URL
    scraper_api_url: str = "http://localhost:3001"
    
    @property
    def is_local(self) -> bool:
        """Check if running in local mode."""
        return self.mode == Mode.LOCAL
    
    @property
    def is_cloud(self) -> bool:
        """Check if running in cloud mode."""
        return self.mode == Mode.CLOUD
    
    @classmethod
    def from_environment(cls) -> "Config":
        """Create configuration from environment variables."""
        # Determine mode
        mode_str = os.environ.get("MODE", "local").lower()
        mode = Mode.CLOUD if mode_str == "cloud" else Mode.LOCAL
        
        # GCP project ID (required for cloud mode)
        gcp_project_id = os.environ.get("GCP_PROJECT_ID", "")
        
        if mode == Mode.CLOUD and not gcp_project_id:
            raise ValueError("GCP_PROJECT_ID environment variable is required in cloud mode")
        
        config = cls(
            mode=mode,
            gcp_project_id=gcp_project_id,
            gcp_region=os.environ.get("GCP_REGION", "us-central1"),
            gcp_service_account=os.environ.get("GCP_SERVICE_ACCOUNT"),
            data_dir=os.environ.get("DATA_DIR", "./data"),
            firestore_collection_prefix=os.environ.get(
                "FIRESTORE_COLLECTION_PREFIX", "creative_ads"
            ),
            storage_bucket_raw=os.environ.get(
                "STORAGE_BUCKET_RAW", f"{gcp_project_id}-raw-assets" if gcp_project_id else ""
            ),
            storage_bucket_processed=os.environ.get(
                "STORAGE_BUCKET_PROCESSED", f"{gcp_project_id}-processed-assets" if gcp_project_id else ""
            ),
            pubsub_topic=os.environ.get("PUBSUB_TOPIC", "agentic-ads-jobs"),
            pubsub_subscription=os.environ.get(
                "PUBSUB_SUBSCRIPTION", "agentic-ads-jobs-sub"
            ),
            bigquery_enabled=os.environ.get("BIGQUERY_ENABLED", "false").lower() == "true",
            max_concurrent_jobs=int(os.environ.get("MAX_CONCURRENT_JOBS", "10")),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            dashboard_port=int(os.environ.get("DASHBOARD_PORT", "8080")),
            api_port=int(os.environ.get("API_PORT", "8081")),
            scraper_api_url=os.environ.get("SCRAPER_API_URL", "http://localhost:3001"),
        )
        
        # Configure mode-specific settings
        if mode == Mode.CLOUD:
            # Cloud mode: Enable cloud services
            config.enable_cloud_monitoring = True
            config.enable_cloud_logging = True
            config.llm_mode = "vertex"
            
            # Configure Vertex AI
            config.vertex_ai = VertexAIConfig(
                project_id=gcp_project_id,
                location=os.environ.get("VERTEX_AI_LOCATION", "us-central1"),
                model_name=os.environ.get("VERTEX_AI_MODEL", "gemini-1.5-pro"),
                endpoint_id=os.environ.get("VERTEX_AI_ENDPOINT_ID"),
            )
        else:
            # Local mode: Configure local alternatives
            config.enable_cloud_monitoring = False
            config.enable_cloud_logging = False
            
            # LLM mode for local
            llm_mode = os.environ.get("LLM_MODE", "template")
            if llm_mode == "vertex":
                # CRITICAL: Prevent Vertex in local mode
                raise ValueError(
                    "LLM_MODE=vertex is not allowed in local mode. "
                    "Use LLM_MODE=template or LLM_MODE=ollama for local development."
                )
            config.llm_mode = llm_mode
            
            # Configure Ollama if enabled
            if llm_mode == "ollama":
                config.ollama = OllamaConfig(
                    host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
                    model=os.environ.get("OLLAMA_MODEL", "llama2"),
                    enabled=True,
                )
            
            # Enforce low-RAM settings in local mode
            config.low_ram = LowRAMConfig(
                max_browser_instances=int(os.environ.get("MAX_BROWSER_INSTANCES", "1")),
                browser_headless=os.environ.get("BROWSER_HEADLESS", "true").lower() == "true",
                sequential_scraping=os.environ.get("SEQUENTIAL_SCRAPING", "true").lower() == "true",
                max_concurrent_scrapes=int(os.environ.get("MAX_CONCURRENT_SCRAPES", "1")),
                image_only_mode=os.environ.get("IMAGE_ONLY_MODE", "true").lower() == "true",
                max_image_dimension=int(os.environ.get("MAX_IMAGE_DIMENSION", "1920")),
                video_frame_sample_limit=int(os.environ.get("VIDEO_FRAME_SAMPLE_LIMIT", "10")),
                global_job_cap=int(os.environ.get("GLOBAL_JOB_CAP", "100")),
                max_queue_size=int(os.environ.get("MAX_QUEUE_SIZE", "1000")),
                max_assets_in_memory=int(os.environ.get("MAX_ASSETS_IN_MEMORY", "50")),
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
        # Determine mode
        mode_str = data.pop('mode', 'local').lower()
        mode = Mode.CLOUD if mode_str == 'cloud' else Mode.LOCAL
        
        # Extract Vertex AI config if present
        vertex_ai_data = data.pop('vertex_ai', None)
        vertex_ai = None
        if vertex_ai_data and mode == Mode.CLOUD:
            vertex_ai = VertexAIConfig(**vertex_ai_data)
        
        # Extract Ollama config if present
        ollama_data = data.pop('ollama', None)
        ollama = OllamaConfig(**ollama_data) if ollama_data else OllamaConfig()
        
        # Extract low-RAM config if present
        low_ram_data = data.pop('low_ram', None)
        low_ram = LowRAMConfig(**low_ram_data) if low_ram_data else LowRAMConfig()
        
        # Extract scraper configs
        scrapers_data = data.pop('scrapers', {})
        scrapers = {}
        for source_name, scraper_data in scrapers_data.items():
            source = ScraperSource(source_name)
            scrapers[source] = ScraperConfig(source=source, **scraper_data)
        
        return cls(
            **data,
            mode=mode,
            vertex_ai=vertex_ai,
            ollama=ollama,
            low_ram=low_ram,
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
            "mode": self.mode.value,
            "gcp_project_id": self.gcp_project_id,
            "gcp_region": self.gcp_region,
            "gcp_service_account": self.gcp_service_account,
            "data_dir": self.data_dir,
            "firestore_collection_prefix": self.firestore_collection_prefix,
            "storage_bucket_raw": self.storage_bucket_raw,
            "storage_bucket_processed": self.storage_bucket_processed,
            "pubsub_topic": self.pubsub_topic,
            "pubsub_subscription": self.pubsub_subscription,
            "bigquery_enabled": self.bigquery_enabled,
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "log_level": self.log_level,
            "llm_mode": self.llm_mode,
            "enable_cloud_monitoring": self.enable_cloud_monitoring,
            "enable_cloud_logging": self.enable_cloud_logging,
            "vertex_ai": {
                "project_id": self.vertex_ai.project_id,
                "location": self.vertex_ai.location,
                "model_name": self.vertex_ai.model_name,
            } if self.vertex_ai else None,
            "ollama": {
                "host": self.ollama.host,
                "model": self.ollama.model,
                "enabled": self.ollama.enabled,
            },
            "low_ram": {
                "max_browser_instances": self.low_ram.max_browser_instances,
                "sequential_scraping": self.low_ram.sequential_scraping,
                "global_job_cap": self.low_ram.global_job_cap,
            },
        }
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        if self.mode == Mode.CLOUD:
            if not self.gcp_project_id:
                errors.append("GCP_PROJECT_ID is required in cloud mode")
            if not self.vertex_ai:
                errors.append("Vertex AI configuration is required in cloud mode")
        
        if self.llm_mode == "vertex" and self.mode != Mode.CLOUD:
            errors.append("Vertex AI LLM is only available in cloud mode")
        
        return errors
