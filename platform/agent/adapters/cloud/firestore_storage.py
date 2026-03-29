"""
Firestore Storage Adapter

Implements StorageInterface using Google Cloud Firestore.
CLOUD MODE ONLY.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional

from agent.interfaces.storage import StorageInterface, AssetData

logger = logging.getLogger(__name__)


class FirestoreStorage(StorageInterface):
    """
    Google Cloud Firestore storage implementation.
    
    Collections:
    - {prefix}_assets: Creative ad assets with features and prompts
    - {prefix}_jobs: Processing job records
    - {prefix}_metrics: Aggregated metrics and statistics
    
    CLOUD MODE ONLY - requires GCP credentials.
    """
    
    def __init__(
        self,
        project_id: str,
        collection_prefix: str = "creative_ads",
        database_id: str = "(default)",
        storage_bucket_raw: Optional[str] = None,
        storage_bucket_processed: Optional[str] = None,
    ):
        self._validate_mode()
        
        self.project_id = project_id
        self.collection_prefix = collection_prefix
        self.database_id = database_id
        self.storage_bucket_raw = storage_bucket_raw or f"{project_id}-raw-assets"
        self.storage_bucket_processed = storage_bucket_processed or f"{project_id}-processed-assets"
        
        self._firestore_client = None
        self._storage_client = None
        self._raw_bucket = None
        self._processed_bucket = None
        
    def _validate_mode(self) -> None:
        """Validate that we're in cloud mode."""
        mode = os.environ.get("MODE", "local").lower()
        if mode != "cloud":
            raise RuntimeError(
                "FirestoreStorage is only available in cloud mode. "
                "Set MODE=cloud to use cloud adapters, or use LocalStorage for local development."
            )
    
    async def connect(self) -> None:
        """Initialize Firestore and Cloud Storage connections."""
        from google.cloud import firestore
        from google.cloud import storage
        
        # Initialize Firestore
        self._firestore_client = firestore.AsyncClient(
            project=self.project_id,
            database=self.database_id
        )
        
        # Initialize Cloud Storage
        self._storage_client = storage.Client(project=self.project_id)
        self._raw_bucket = self._storage_client.bucket(self.storage_bucket_raw)
        self._processed_bucket = self._storage_client.bucket(self.storage_bucket_processed)
        
        logger.info(f"Connected to Firestore: {self.project_id}/{self.database_id}")
        logger.info(f"Connected to Cloud Storage: {self.storage_bucket_raw}, {self.storage_bucket_processed}")
    
    async def close(self) -> None:
        """Close connections."""
        if self._firestore_client:
            self._firestore_client.close()
        logger.info("Firestore connection closed")
    
    async def health_check(self) -> bool:
        """Check if storage is healthy."""
        try:
            # Try to list one document
            collection = self._collection("assets")
            async for _ in collection.limit(1).stream():
                break
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def _collection(self, name: str):
        """Get a collection reference with prefix."""
        return self._firestore_client.collection(f"{self.collection_prefix}_{name}")
    
    # Asset Operations
    
    async def store_asset(self, asset_id: str, data: Dict[str, Any]) -> str:
        """Store a new creative asset."""
        now = datetime.utcnow()
        
        doc_data = {
            **data,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        doc_ref = self._collection("assets").document(asset_id)
        await doc_ref.set(doc_data)
        
        logger.debug(f"Stored asset: {asset_id}")
        return asset_id
    
    async def get_asset(self, asset_id: str) -> Optional[AssetData]:
        """Retrieve a creative asset by ID."""
        doc_ref = self._collection("assets").document(asset_id)
        doc = await doc_ref.get()
        
        if doc.exists:
            return AssetData.from_dict({"id": asset_id, **doc.to_dict()})
        return None
    
    async def update_asset(self, asset_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing asset."""
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        doc_ref = self._collection("assets").document(asset_id)
        await doc_ref.update(updates)
        
        logger.debug(f"Updated asset: {asset_id}")
    
    async def delete_asset(self, asset_id: str) -> None:
        """Delete an asset."""
        doc_ref = self._collection("assets").document(asset_id)
        await doc_ref.delete()
        
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
        query = self._collection("assets")
        
        if industry:
            query = query.where("industry", "==", industry)
        
        if source:
            query = query.where("source", "==", source)
        
        if has_prompt is not None:
            if has_prompt:
                query = query.where("reverse_prompt", "!=", None)
            else:
                query = query.where("reverse_prompt", "==", None)
        
        query = query.limit(limit).offset(offset)
        
        results = []
        async for doc in query.stream():
            results.append(AssetData.from_dict({"id": doc.id, **doc.to_dict()}))
        
        return results
    
    async def count_assets(
        self,
        industry: Optional[str] = None,
        source: Optional[str] = None
    ) -> int:
        """Count assets matching criteria."""
        query = self._collection("assets")
        
        if industry:
            query = query.where("industry", "==", industry)
        
        if source:
            query = query.where("source", "==", source)
        
        # Use count aggregation
        from google.cloud.firestore_v1.aggregation import AggregationQuery
        
        agg_query = AggregationQuery(query)
        agg_query.count()
        
        results = await agg_query.get()
        for result in results:
            return result[0].value
        
        return 0
    
    async def stream_assets(
        self,
        batch_size: int = 100
    ) -> AsyncIterator[List[AssetData]]:
        """Stream all assets in batches."""
        query = self._collection("assets").limit(batch_size)
        last_doc = None
        
        while True:
            if last_doc:
                query = query.start_after(last_doc)
            
            batch = []
            async for doc in query.stream():
                batch.append(AssetData.from_dict({"id": doc.id, **doc.to_dict()}))
                last_doc = doc
            
            if not batch:
                break
            
            yield batch
            
            if len(batch) < batch_size:
                break
    
    # Job Operations
    
    async def store_job(self, job_id: str, job_data: Dict[str, Any]) -> str:
        """Store a job record."""
        doc_ref = self._collection("jobs").document(job_id)
        await doc_ref.set({
            **job_data,
            "created_at": datetime.utcnow().isoformat()
        })
        return job_id
    
    async def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a job by ID."""
        doc_ref = self._collection("jobs").document(job_id)
        doc = await doc_ref.get()
        
        if doc.exists:
            return {"id": job_id, **doc.to_dict()}
        return None
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update job status."""
        updates = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        if result:
            updates["result"] = result
        
        if status in ["completed", "failed"]:
            updates["completed_at"] = datetime.utcnow().isoformat()
        
        doc_ref = self._collection("jobs").document(job_id)
        await doc_ref.update(updates)
    
    async def query_jobs(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query jobs with filters."""
        query = self._collection("jobs")
        
        if status:
            query = query.where("status", "==", status)
        
        if job_type:
            query = query.where("job_type", "==", job_type)
        
        query = query.limit(limit)
        
        results = []
        async for doc in query.stream():
            results.append({"id": doc.id, **doc.to_dict()})
        
        return results
    
    # Metrics Operations
    
    async def increment_metric(
        self,
        metric_name: str,
        increment: int = 1,
        dimensions: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a metric counter."""
        from google.cloud.firestore import Increment
        
        doc_id = f"{metric_name}_{datetime.utcnow().strftime('%Y%m%d')}"
        doc_ref = self._collection("metrics").document(doc_id)
        
        await doc_ref.set({
            "name": metric_name,
            "count": Increment(increment),
            "dimensions": dimensions or {},
            "updated_at": datetime.utcnow().isoformat()
        }, merge=True)
    
    async def get_metrics_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get aggregated metrics summary."""
        query = self._collection("metrics")
        
        summary = {
            "total_assets": 0,
            "by_source": {},
            "by_industry": {},
            "prompts_generated": 0
        }
        
        async for doc in query.stream():
            data = doc.to_dict()
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
        """Upload a file to Cloud Storage."""
        target_bucket = self._raw_bucket if bucket == "raw" else self._processed_bucket
        
        blob = target_bucket.blob(f"assets/{file_id}")
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: blob.upload_from_string(data, content_type=content_type)
        )
        
        logger.debug(f"Uploaded file: {file_id}")
        return f"gs://{target_bucket.name}/assets/{file_id}"
    
    async def download_file(self, path: str) -> Optional[bytes]:
        """Download a file from Cloud Storage."""
        try:
            # Parse GCS path
            if path.startswith("gs://"):
                parts = path[5:].split("/", 1)
                bucket_name = parts[0]
                blob_path = parts[1] if len(parts) > 1 else ""
            else:
                return None
            
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            data = await asyncio.get_event_loop().run_in_executor(
                None,
                blob.download_as_bytes
            )
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return None
    
    async def delete_file(self, path: str) -> bool:
        """Delete a file from Cloud Storage."""
        try:
            if path.startswith("gs://"):
                parts = path[5:].split("/", 1)
                bucket_name = parts[0]
                blob_path = parts[1] if len(parts) > 1 else ""
            else:
                return False
            
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                blob.delete
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    async def get_file_url(
        self,
        path: str,
        expiration_minutes: int = 60
    ) -> Optional[str]:
        """Get a signed URL for accessing a file."""
        try:
            if path.startswith("gs://"):
                parts = path[5:].split("/", 1)
                bucket_name = parts[0]
                blob_path = parts[1] if len(parts) > 1 else ""
            else:
                return None
            
            bucket = self._storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            url = blob.generate_signed_url(
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            return None

