"""
Local Storage Adapter

Implements StorageInterface using local filesystem:
- JSON files for document storage (Firestore emulation)
- Local filesystem for file storage (GCS emulation)

Data is stored in:
- /data/db/*.json - Document collections
- /data/assets/ - Raw and processed files
"""

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from agent.interfaces.storage import StorageInterface, AssetData

logger = logging.getLogger(__name__)


class LocalStorage(StorageInterface):
    """
    Local storage implementation using filesystem.
    
    Emulates:
    - Firestore: JSON files in /data/db/
    - Cloud Storage: Files in /data/assets/
    """
    
    def __init__(
        self,
        data_dir: str = "./data",
        collection_prefix: str = "creative_ads"
    ):
        self.data_dir = Path(data_dir)
        self.collection_prefix = collection_prefix
        
        # Paths
        self.db_dir = self.data_dir / "db"
        self.assets_dir = self.data_dir / "assets"
        self.raw_dir = self.assets_dir / "raw"
        self.processed_dir = self.assets_dir / "processed"
        
        # In-memory cache for faster reads
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_dirty: Dict[str, bool] = {}
        
    async def connect(self) -> None:
        """Initialize local storage directories."""
        logger.info(f"Initializing local storage at {self.data_dir}")
        
        # Create directories
        for dir_path in [self.db_dir, self.raw_dir, self.processed_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing collections into cache
        await self._load_collections()
        
        logger.info("Local storage initialized")
    
    async def close(self) -> None:
        """Flush cache and close storage."""
        await self._flush_all()
        logger.info("Local storage closed")
    
    async def health_check(self) -> bool:
        """Check if storage is healthy."""
        try:
            return self.data_dir.exists() and self.db_dir.exists()
        except Exception:
            return False
    
    # Internal methods
    
    def _collection_path(self, name: str) -> Path:
        """Get path for a collection JSON file."""
        return self.db_dir / f"{self.collection_prefix}_{name}.json"
    
    async def _load_collections(self) -> None:
        """Load all collections into memory."""
        for collection_file in self.db_dir.glob(f"{self.collection_prefix}_*.json"):
            collection_name = collection_file.stem.replace(f"{self.collection_prefix}_", "")
            try:
                with open(collection_file, 'r') as f:
                    self._cache[collection_name] = json.load(f)
                self._cache_dirty[collection_name] = False
            except Exception as e:
                logger.error(f"Failed to load collection {collection_name}: {e}")
                self._cache[collection_name] = {}
    
    async def _get_collection(self, name: str) -> Dict[str, Any]:
        """Get a collection, creating it if it doesn't exist."""
        if name not in self._cache:
            self._cache[name] = {}
            self._cache_dirty[name] = True
        return self._cache[name]
    
    async def _save_collection(self, name: str) -> None:
        """Save a collection to disk."""
        if not self._cache_dirty.get(name, False):
            return
            
        path = self._collection_path(name)
        try:
            with open(path, 'w') as f:
                json.dump(self._cache.get(name, {}), f, indent=2, default=str)
            self._cache_dirty[name] = False
        except Exception as e:
            logger.error(f"Failed to save collection {name}: {e}")
    
    async def _flush_all(self) -> None:
        """Flush all dirty collections to disk."""
        for name in self._cache_dirty:
            await self._save_collection(name)
    
    # Asset Operations
    
    async def store_asset(self, asset_id: str, data: Dict[str, Any]) -> str:
        """Store a new creative asset."""
        now = datetime.utcnow().isoformat()
        
        doc_data = {
            **data,
            "created_at": now,
            "updated_at": now
        }
        
        collection = await self._get_collection("assets")
        collection[asset_id] = doc_data
        self._cache_dirty["assets"] = True
        
        # Periodic flush (every 10 writes)
        if len(collection) % 10 == 0:
            await self._save_collection("assets")
        
        logger.debug(f"Stored asset: {asset_id}")
        return asset_id
    
    async def get_asset(self, asset_id: str) -> Optional[AssetData]:
        """Retrieve a creative asset by ID."""
        collection = await self._get_collection("assets")
        data = collection.get(asset_id)
        
        if data:
            return AssetData.from_dict({"id": asset_id, **data})
        return None
    
    async def update_asset(self, asset_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing asset."""
        collection = await self._get_collection("assets")
        
        if asset_id in collection:
            updates["updated_at"] = datetime.utcnow().isoformat()
            collection[asset_id].update(updates)
            self._cache_dirty["assets"] = True
            logger.debug(f"Updated asset: {asset_id}")
    
    async def delete_asset(self, asset_id: str) -> None:
        """Delete an asset."""
        collection = await self._get_collection("assets")
        
        if asset_id in collection:
            del collection[asset_id]
            self._cache_dirty["assets"] = True
            logger.debug(f"Deleted asset: {asset_id}")
    
    async def query_assets(
        self,
        industry: Optional[str] = None,
        source: Optional[str] = None,
        has_prompt: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AssetData]:
        """Query assets with filters."""
        collection = await self._get_collection("assets")
        
        results = []
        for asset_id, data in collection.items():
            # Apply filters
            if industry and data.get("industry") != industry:
                continue
            if source and data.get("source") != source:
                continue
            if has_prompt is not None:
                has_reverse_prompt = data.get("reverse_prompt") is not None
                if has_prompt != has_reverse_prompt:
                    continue
            
            results.append(AssetData.from_dict({"id": asset_id, **data}))
        
        # Apply offset and limit
        return results[offset:offset + limit]
    
    async def count_assets(
        self,
        industry: Optional[str] = None,
        source: Optional[str] = None
    ) -> int:
        """Count assets matching criteria."""
        collection = await self._get_collection("assets")
        
        count = 0
        for data in collection.values():
            if industry and data.get("industry") != industry:
                continue
            if source and data.get("source") != source:
                continue
            count += 1
        
        return count
    
    async def stream_assets(
        self,
        batch_size: int = 100
    ) -> AsyncIterator[List[AssetData]]:
        """Stream all assets in batches."""
        collection = await self._get_collection("assets")
        items = list(collection.items())
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            yield [
                AssetData.from_dict({"id": asset_id, **data})
                for asset_id, data in batch
            ]
    
    # Job Operations
    
    async def store_job(self, job_id: str, job_data: Dict[str, Any]) -> str:
        """Store a job record."""
        collection = await self._get_collection("jobs")
        
        collection[job_id] = {
            **job_data,
            "created_at": datetime.utcnow().isoformat()
        }
        self._cache_dirty["jobs"] = True
        
        return job_id
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a job by ID."""
        collection = await self._get_collection("jobs")
        return collection.get(job_id)
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update job status."""
        collection = await self._get_collection("jobs")
        
        if job_id in collection:
            updates = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            if result:
                updates["result"] = result
            
            if status in ["completed", "failed"]:
                updates["completed_at"] = datetime.utcnow().isoformat()
            
            collection[job_id].update(updates)
            self._cache_dirty["jobs"] = True
    
    async def query_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query jobs with filters."""
        collection = await self._get_collection("jobs")
        
        results = []
        for job_id, data in collection.items():
            if status and data.get("status") != status:
                continue
            if job_type and data.get("job_type") != job_type:
                continue
            
            results.append({"id": job_id, **data})
            
            if len(results) >= limit:
                break
        
        return results
    
    # Metrics Operations
    
    async def increment_metric(
        self,
        metric_name: str,
        increment: int = 1,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a metric counter."""
        collection = await self._get_collection("metrics")
        
        date_key = datetime.utcnow().strftime('%Y%m%d')
        metric_id = f"{metric_name}_{date_key}"
        
        if metric_id not in collection:
            collection[metric_id] = {
                "name": metric_name,
                "count": 0,
                "dimensions": dimensions or {},
            }
        
        collection[metric_id]["count"] += increment
        collection[metric_id]["updated_at"] = datetime.utcnow().isoformat()
        self._cache_dirty["metrics"] = True
    
    async def get_metrics_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregated metrics summary."""
        collection = await self._get_collection("metrics")
        
        summary = {
            "total_assets": 0,
            "by_source": {},
            "by_industry": {},
            "prompts_generated": 0
        }
        
        for metric_id, data in collection.items():
            name = data.get("name", "")
            count = data.get("count", 0)
            
            if name == "assets_scraped":
                summary["total_assets"] += count
            elif name == "prompts_generated":
                summary["prompts_generated"] += count
            elif name.startswith("source_"):
                source = name.replace("source_", "")
                summary["by_source"][source] = summary["by_source"].get(source, 0) + count
            elif name.startswith("industry_"):
                industry = name.replace("industry_", "")
                summary["by_industry"][industry] = summary["by_industry"].get(industry, 0) + count
        
        return summary
    
    # File Storage Operations
    
    async def upload_file(
        self,
        file_id: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        bucket: str = "raw"
    ) -> str:
        """Upload a file to local storage."""
        if bucket == "raw":
            target_dir = self.raw_dir
        else:
            target_dir = self.processed_dir
        
        # Determine extension from content type
        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
        }
        ext = ext_map.get(content_type, "")
        
        file_path = target_dir / f"{file_id}{ext}"
        
        with open(file_path, 'wb') as f:
            f.write(data)
        
        logger.debug(f"Uploaded file: {file_path}")
        return str(file_path)
    
    async def download_file(self, path: str) -> Optional[bytes]:
        """Download a file from local storage."""
        try:
            file_path = Path(path)
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
        return None
    
    async def delete_file(self, path: str) -> bool:
        """Delete a file from local storage."""
        try:
            file_path = Path(path)
            if file_path.exists():
                file_path.unlink()
                return True
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
        return False
    
    async def get_file_url(
        self,
        path: str,
        expiration_minutes: int = 60
    ) -> Optional[str]:
        """Get local file path (no signing needed for local)."""
        file_path = Path(path)
        if file_path.exists():
            return f"file://{file_path.absolute()}"
        return None

