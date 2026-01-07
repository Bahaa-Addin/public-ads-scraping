"""
Storage Interface

Defines the contract for all storage operations.
Implementations: LocalStorage (filesystem), FirestoreStorage (cloud)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncIterator


@dataclass
class AssetData:
    """Represents a creative asset in storage."""
    id: str
    source: str
    source_url: Optional[str] = None
    image_url: Optional[str] = None
    asset_type: str = "image"
    
    # Metadata
    advertiser_name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    
    # Extracted features
    features: Optional[Dict[str, Any]] = None
    
    # Classification
    industry: Optional[str] = None
    industry_tags: Optional[Dict[str, Any]] = None
    
    # Generated prompts
    reverse_prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    prompt_metadata: Optional[Dict[str, Any]] = None
    
    # File storage references
    raw_asset_path: Optional[str] = None
    processed_asset_path: Optional[str] = None
    
    # Timestamps
    scraped_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = {
            "id": self.id,
            "source": self.source,
            "source_url": self.source_url,
            "image_url": self.image_url,
            "asset_type": self.asset_type,
            "advertiser_name": self.advertiser_name,
            "title": self.title,
            "description": self.description,
            "features": self.features,
            "industry": self.industry,
            "industry_tags": self.industry_tags,
            "reverse_prompt": self.reverse_prompt,
            "negative_prompt": self.negative_prompt,
            "prompt_metadata": self.prompt_metadata,
            "raw_asset_path": self.raw_asset_path,
            "processed_asset_path": self.processed_asset_path,
        }
        
        # Convert datetime objects to ISO strings
        for key in ['scraped_at', 'processed_at', 'created_at', 'updated_at']:
            value = getattr(self, key)
            data[key] = value.isoformat() if value else None
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AssetData":
        """Create from dictionary."""
        from dataclasses import fields
        
        # Get valid field names from dataclass
        valid_fields = {f.name for f in fields(cls)}
        
        # Convert ISO strings back to datetime
        for key in ['scraped_at', 'processed_at', 'created_at', 'updated_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        
        # Filter to only valid fields and provide defaults for required fields
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        # Ensure required fields have values
        if 'id' not in filtered_data:
            filtered_data['id'] = data.get('id', 'unknown')
        if 'source' not in filtered_data:
            filtered_data['source'] = data.get('source', 'unknown')
        
        return cls(**filtered_data)


class StorageInterface(ABC):
    """
    Abstract interface for storage operations.
    
    Implementations:
    - LocalStorage: JSON files + filesystem for local development
    - FirestoreStorage: Google Cloud Firestore for production
    """
    
    @abstractmethod
    async def connect(self) -> None:
        """Initialize storage connection."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close storage connection."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if storage is healthy and accessible."""
        pass
    
    # Asset Operations
    
    @abstractmethod
    async def store_asset(self, asset_id: str, data: Dict[str, Any]) -> str:
        """Store a new creative asset. Returns the asset ID."""
        pass
    
    @abstractmethod
    async def get_asset(self, asset_id: str) -> Optional[AssetData]:
        """Retrieve a creative asset by ID."""
        pass
    
    @abstractmethod
    async def update_asset(self, asset_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing asset with partial data."""
        pass
    
    @abstractmethod
    async def delete_asset(self, asset_id: str) -> None:
        """Delete an asset."""
        pass
    
    @abstractmethod
    async def query_assets(
        self,
        industry: Optional[str] = None,
        source: Optional[str] = None,
        has_prompt: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AssetData]:
        """Query assets with filters."""
        pass
    
    @abstractmethod
    async def count_assets(
        self,
        industry: Optional[str] = None,
        source: Optional[str] = None
    ) -> int:
        """Count assets matching criteria."""
        pass
    
    @abstractmethod
    async def stream_assets(
        self,
        batch_size: int = 100
    ) -> AsyncIterator[List[AssetData]]:
        """Stream all assets in batches."""
        pass
    
    # Job Operations
    
    @abstractmethod
    async def store_job(self, job_id: str, job_data: Dict[str, Any]) -> str:
        """Store a job record."""
        pass
    
    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a job by ID."""
        pass
    
    @abstractmethod
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update job status."""
        pass
    
    @abstractmethod
    async def query_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query jobs with filters."""
        pass
    
    # Metrics Operations
    
    @abstractmethod
    async def increment_metric(
        self,
        metric_name: str,
        increment: int = 1,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a metric counter."""
        pass
    
    @abstractmethod
    async def get_metrics_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregated metrics summary."""
        pass
    
    # File Storage Operations
    
    @abstractmethod
    async def upload_file(
        self,
        file_id: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        bucket: str = "raw"
    ) -> str:
        """Upload a file and return the storage path."""
        pass
    
    @abstractmethod
    async def download_file(self, path: str) -> Optional[bytes]:
        """Download a file by path."""
        pass
    
    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete a file by path."""
        pass
    
    @abstractmethod
    async def get_file_url(
        self,
        path: str,
        expiration_minutes: int = 60
    ) -> Optional[str]:
        """Get a URL for accessing a file (signed URL for cloud, local path for local)."""
        pass

