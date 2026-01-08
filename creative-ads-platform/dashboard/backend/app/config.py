"""
Configuration Management for Dashboard Backend

Handles environment variables and settings using pydantic-settings.
"""

import os
from typing import Optional, List
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application
    app_name: str = "Creative Ads Dashboard API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # Local-first mode settings
    mode: str = Field(default="local", alias="MODE")  # "local" or "cloud"
    data_dir: str = Field(default="./data", alias="DATA_DIR")  # Path to local data files
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    
    # GCP
    gcp_project_id: str = Field(default="", alias="GCP_PROJECT_ID")
    gcp_region: str = Field(default="us-central1", alias="GCP_REGION")
    
    # Firestore
    firestore_collection_prefix: str = Field(
        default="creative_ads", 
        alias="FIRESTORE_COLLECTION_PREFIX"
    )
    firestore_database_id: str = Field(default="(default)", alias="FIRESTORE_DATABASE_ID")
    
    # Cloud Storage
    storage_bucket_raw: str = Field(default="", alias="STORAGE_BUCKET_RAW")
    storage_bucket_processed: str = Field(default="", alias="STORAGE_BUCKET_PROCESSED")
    
    # Pub/Sub
    pubsub_topic: str = Field(default="creative-ads-jobs", alias="PUBSUB_TOPIC")
    pubsub_subscription: str = Field(
        default="creative-ads-jobs-sub", 
        alias="PUBSUB_SUBSCRIPTION"
    )
    
    # BigQuery
    bigquery_dataset: str = Field(
        default="creative_ads_analytics", 
        alias="BIGQUERY_DATASET"
    )
    bigquery_enabled: bool = Field(default=False, alias="BIGQUERY_ENABLED")
    
    # Agent Service
    agent_service_url: str = Field(
        default="http://localhost:8080",
        alias="AGENT_SERVICE_URL"
    )
    scraper_service_url: str = Field(
        default="http://localhost:8081",
        alias="SCRAPER_SERVICE_URL"
    )
    
    # Vertex AI
    vertex_ai_location: str = Field(default="us-central1", alias="VERTEX_AI_LOCATION")
    vertex_ai_model: str = Field(default="gemini-1.5-pro", alias="VERTEX_AI_MODEL")
    
    # Authentication
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        alias="SECRET_KEY"
    )
    api_key: Optional[str] = Field(default=None, alias="API_KEY")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS"
    )
    
    # Monitoring
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    enable_cloud_logging: bool = Field(default=True, alias="ENABLE_CLOUD_LOGGING")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    # Cache
    cache_ttl_seconds: int = Field(default=60, alias="CACHE_TTL_SECONDS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        populate_by_name = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set derived values
        if not self.storage_bucket_raw and self.gcp_project_id:
            self.storage_bucket_raw = f"{self.gcp_project_id}-raw-assets"
        if not self.storage_bucket_processed and self.gcp_project_id:
            self.storage_bucket_processed = f"{self.gcp_project_id}-processed-assets"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

