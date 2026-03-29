"""
Firestore, Cloud Storage, and BigQuery Clients

Provides unified access to GCP storage services for the agentic ads platform:
- Firestore: Structured data (ads, features, prompts)
- Cloud Storage: Raw assets (images, videos)
- BigQuery: Analytics and large-scale queries
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncIterator
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class CreativeAsset:
    """Represents a creative ad asset in the database."""
    id: str
    source: str
    source_url: Optional[str]
    image_url: Optional[str]
    asset_type: str  # image, video, carousel
    
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
    
    # Storage references
    raw_asset_path: Optional[str] = None
    processed_asset_path: Optional[str] = None
    
    # Timestamps
    scraped_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore storage."""
        data = asdict(self)
        
        # Convert datetime objects to ISO strings
        for key in ['scraped_at', 'processed_at', 'created_at', 'updated_at']:
            if data.get(key):
                data[key] = data[key].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CreativeAsset":
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        for key in ['scraped_at', 'processed_at', 'created_at', 'updated_at']:
            if data.get(key) and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================================
# Firestore Client
# ============================================================================

class FirestoreClient:
    """
    Async Firestore client for storing and retrieving agentic ads data.
    
    Collections:
    - {prefix}_assets: Creative ad assets with features and prompts
    - {prefix}_jobs: Processing job records
    - {prefix}_metrics: Aggregated metrics and statistics
    """
    
    def __init__(
        self,
        project_id: str,
        collection_prefix: str = "creative_ads",
        database_id: str = "(default)"
    ):
        self.project_id = project_id
        self.collection_prefix = collection_prefix
        self.database_id = database_id
        self._client = None
        self._db = None
        
    async def connect(self) -> None:
        """Initialize Firestore connection."""
        try:
            from google.cloud import firestore
            
            self._client = firestore.AsyncClient(
                project=self.project_id,
                database=self.database_id
            )
            self._db = self._client
            
            logger.info(f"Connected to Firestore: {self.project_id}/{self.database_id}")
            
        except ImportError:
            logger.warning("google-cloud-firestore not installed, using mock client")
            self._client = MockFirestoreClient()
            self._db = self._client
        except Exception as e:
            logger.error(f"Failed to connect to Firestore: {e}")
            raise
    
    async def close(self) -> None:
        """Close Firestore connection."""
        if self._client and hasattr(self._client, 'close'):
            self._client.close()
        logger.info("Firestore connection closed")
    
    def _collection(self, name: str):
        """Get a collection reference with prefix."""
        return self._db.collection(f"{self.collection_prefix}_{name}")
    
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
    
    async def get_asset(self, asset_id: str) -> Optional[CreativeAsset]:
        """Retrieve a creative asset by ID."""
        doc_ref = self._collection("assets").document(asset_id)
        doc = await doc_ref.get()
        
        if doc.exists:
            return CreativeAsset.from_dict({"id": asset_id, **doc.to_dict()})
        
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
    ) -> List[CreativeAsset]:
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
        
        docs = await query.get()
        
        return [
            CreativeAsset.from_dict({"id": doc.id, **doc.to_dict()})
            for doc in docs
        ]
    
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
        
        # Note: Firestore count aggregation requires specific setup
        # This is a simplified version that fetches and counts
        docs = await query.select([]).get()
        return len(docs)
    
    async def stream_assets(
        self,
        batch_size: int = 100
    ) -> AsyncIterator[List[CreativeAsset]]:
        """Stream all assets in batches."""
        query = self._collection("assets").limit(batch_size)
        last_doc = None
        
        while True:
            if last_doc:
                query = query.start_after(last_doc)
            
            docs = await query.get()
            
            if not docs:
                break
            
            assets = [
                CreativeAsset.from_dict({"id": doc.id, **doc.to_dict()})
                for doc in docs
            ]
            
            yield assets
            
            last_doc = docs[-1]
            
            if len(docs) < batch_size:
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
        
        docs = await query.get()
        
        summary = {
            "total_assets": 0,
            "by_source": {},
            "by_industry": {},
            "prompts_generated": 0
        }
        
        for doc in docs:
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


# ============================================================================
# Cloud Storage Client
# ============================================================================

class StorageClient:
    """
    Cloud Storage client for raw asset storage.
    
    Buckets:
    - {project}-raw-assets: Original scraped images/videos
    - {project}-processed-assets: Processed/optimized assets
    """
    
    def __init__(
        self,
        project_id: str,
        raw_bucket: str,
        processed_bucket: str
    ):
        self.project_id = project_id
        self.raw_bucket = raw_bucket
        self.processed_bucket = processed_bucket
        self._client = None
    
    async def connect(self) -> None:
        """Initialize Cloud Storage connection."""
        try:
            from google.cloud import storage
            
            self._client = storage.Client(project=self.project_id)
            
            # Ensure buckets exist
            self._raw_bucket = self._client.bucket(self.raw_bucket)
            self._processed_bucket = self._client.bucket(self.processed_bucket)
            
            logger.info(f"Connected to Cloud Storage: {self.raw_bucket}, {self.processed_bucket}")
            
        except ImportError:
            logger.warning("google-cloud-storage not installed, using mock client")
            self._client = None
        except Exception as e:
            logger.error(f"Failed to connect to Cloud Storage: {e}")
            raise
    
    async def upload_raw_asset(
        self,
        asset_id: str,
        data: bytes,
        content_type: str = "image/jpeg"
    ) -> str:
        """Upload a raw asset to storage."""
        if not self._client:
            logger.warning("Storage client not available")
            return f"gs://{self.raw_bucket}/{asset_id}"
        
        blob = self._raw_bucket.blob(f"assets/{asset_id}")
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: blob.upload_from_string(data, content_type=content_type)
        )
        
        logger.debug(f"Uploaded raw asset: {asset_id}")
        return f"gs://{self.raw_bucket}/assets/{asset_id}"
    
    async def upload_processed_asset(
        self,
        asset_id: str,
        data: bytes,
        content_type: str = "image/webp"
    ) -> str:
        """Upload a processed asset to storage."""
        if not self._client:
            return f"gs://{self.processed_bucket}/{asset_id}"
        
        blob = self._processed_bucket.blob(f"processed/{asset_id}")
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: blob.upload_from_string(data, content_type=content_type)
        )
        
        logger.debug(f"Uploaded processed asset: {asset_id}")
        return f"gs://{self.processed_bucket}/processed/{asset_id}"
    
    async def download_asset(self, gcs_path: str) -> Optional[bytes]:
        """Download an asset from storage."""
        if not self._client:
            return None
        
        try:
            # Parse GCS path
            if gcs_path.startswith("gs://"):
                parts = gcs_path[5:].split("/", 1)
                bucket_name = parts[0]
                blob_path = parts[1] if len(parts) > 1 else ""
            else:
                return None
            
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            data = await asyncio.get_event_loop().run_in_executor(
                None,
                blob.download_as_bytes
            )
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to download asset: {e}")
            return None
    
    async def get_signed_url(
        self,
        gcs_path: str,
        expiration_minutes: int = 60
    ) -> Optional[str]:
        """Generate a signed URL for temporary access."""
        if not self._client:
            return None
        
        try:
            from datetime import timedelta
            
            parts = gcs_path[5:].split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1] if len(parts) > 1 else ""
            
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            url = blob.generate_signed_url(
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            return None
    
    async def delete_asset(self, gcs_path: str) -> bool:
        """Delete an asset from storage."""
        if not self._client:
            return False
        
        try:
            parts = gcs_path[5:].split("/", 1)
            bucket_name = parts[0]
            blob_path = parts[1] if len(parts) > 1 else ""
            
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                blob.delete
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete asset: {e}")
            return False


# ============================================================================
# BigQuery Client
# ============================================================================

class BigQueryClient:
    """
    BigQuery client for analytics and large-scale data processing.
    
    Tables:
    - {dataset}.assets: Denormalized asset data for analytics
    - {dataset}.features: Feature vectors for ML
    - {dataset}.prompts: Generated prompts history
    """
    
    def __init__(
        self,
        project_id: str,
        dataset_id: str = "creative_ads_analytics"
    ):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self._client = None
    
    async def connect(self) -> None:
        """Initialize BigQuery connection."""
        try:
            from google.cloud import bigquery
            
            self._client = bigquery.Client(project=self.project_id)
            
            # Ensure dataset exists
            dataset_ref = self._client.dataset(self.dataset_id)
            try:
                self._client.get_dataset(dataset_ref)
            except Exception:
                dataset = bigquery.Dataset(dataset_ref)
                dataset.location = "US"
                self._client.create_dataset(dataset, exists_ok=True)
            
            logger.info(f"Connected to BigQuery: {self.project_id}.{self.dataset_id}")
            
        except ImportError:
            logger.warning("google-cloud-bigquery not installed")
            self._client = None
        except Exception as e:
            logger.error(f"Failed to connect to BigQuery: {e}")
    
    async def insert_asset_row(self, asset: CreativeAsset) -> None:
        """Insert or update an asset row."""
        if not self._client:
            return
        
        table_id = f"{self.project_id}.{self.dataset_id}.assets"
        
        row = {
            "asset_id": asset.id,
            "source": asset.source,
            "industry": asset.industry,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
            "has_features": asset.features is not None,
            "has_prompt": asset.reverse_prompt is not None,
        }
        
        # Add flattened features
        if asset.features:
            row["layout_type"] = asset.features.get("layout_type")
            row["focal_point"] = asset.features.get("focal_point")
            row["quality_score"] = asset.features.get("quality_score")
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._client.insert_rows_json(table_id, [row])
        )
    
    async def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute a BigQuery SQL query."""
        if not self._client:
            return []
        
        query_job = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._client.query(sql)
        )
        
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: list(query_job.result())
        )
        
        return [dict(row) for row in results]
    
    async def get_industry_distribution(self) -> Dict[str, int]:
        """Get asset count by industry."""
        sql = f"""
        SELECT industry, COUNT(*) as count
        FROM `{self.project_id}.{self.dataset_id}.assets`
        GROUP BY industry
        ORDER BY count DESC
        """
        
        results = await self.query(sql)
        return {row["industry"]: row["count"] for row in results}
    
    async def get_source_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics by source."""
        sql = f"""
        SELECT 
            source,
            COUNT(*) as total,
            COUNTIF(has_features) as with_features,
            COUNTIF(has_prompt) as with_prompts,
            AVG(quality_score) as avg_quality
        FROM `{self.project_id}.{self.dataset_id}.assets`
        GROUP BY source
        """
        
        results = await self.query(sql)
        return {
            row["source"]: {
                "total": row["total"],
                "with_features": row["with_features"],
                "with_prompts": row["with_prompts"],
                "avg_quality": row["avg_quality"]
            }
            for row in results
        }


# ============================================================================
# Mock Client for Development
# ============================================================================

class MockFirestoreClient:
    """Mock Firestore client for local development."""
    
    def __init__(self):
        self._data: Dict[str, Dict[str, Dict]] = {}
    
    def collection(self, name: str):
        if name not in self._data:
            self._data[name] = {}
        return MockCollection(self._data[name])


class MockCollection:
    """Mock Firestore collection."""
    
    def __init__(self, data: Dict[str, Dict]):
        self._data = data
    
    def document(self, doc_id: str):
        return MockDocument(self._data, doc_id)
    
    def where(self, field: str, op: str, value: Any):
        return self
    
    def limit(self, n: int):
        return self
    
    def offset(self, n: int):
        return self
    
    def select(self, fields: List[str]):
        return self
    
    def start_after(self, doc):
        return self
    
    async def get(self):
        return [
            MockDocumentSnapshot(doc_id, data)
            for doc_id, data in self._data.items()
        ]


class MockDocument:
    """Mock Firestore document reference."""
    
    def __init__(self, collection_data: Dict[str, Dict], doc_id: str):
        self._collection_data = collection_data
        self._doc_id = doc_id
    
    async def set(self, data: Dict, merge: bool = False):
        if merge and self._doc_id in self._collection_data:
            self._collection_data[self._doc_id].update(data)
        else:
            self._collection_data[self._doc_id] = data
    
    async def update(self, data: Dict):
        if self._doc_id in self._collection_data:
            self._collection_data[self._doc_id].update(data)
    
    async def get(self):
        data = self._collection_data.get(self._doc_id)
        return MockDocumentSnapshot(self._doc_id, data)
    
    async def delete(self):
        if self._doc_id in self._collection_data:
            del self._collection_data[self._doc_id]


class MockDocumentSnapshot:
    """Mock Firestore document snapshot."""
    
    def __init__(self, doc_id: str, data: Optional[Dict]):
        self.id = doc_id
        self._data = data
    
    @property
    def exists(self) -> bool:
        return self._data is not None
    
    def to_dict(self) -> Optional[Dict]:
        return self._data

