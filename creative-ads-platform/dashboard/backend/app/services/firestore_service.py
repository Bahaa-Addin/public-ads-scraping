"""
Firestore Service for Dashboard

Provides data access layer for Firestore operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache

from ..config import get_settings, Settings
from ..models import (
    Asset, Job, JobStatus, JobType, ScraperSource, IndustryCategory,
    AssetFilterParams
)

logger = logging.getLogger(__name__)


class FirestoreService:
    """Service for Firestore database operations."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = None
        self._mock_data = self._init_mock_data()
    
    @property
    def client(self):
        """Get Firestore client (lazy initialization)."""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def _initialize_client(self):
        """Initialize Firestore client."""
        if not self.settings.gcp_project_id:
            logger.warning("No GCP project ID, using mock client")
            return
        
        try:
            from google.cloud import firestore
            self._client = firestore.AsyncClient(
                project=self.settings.gcp_project_id,
                database=self.settings.firestore_database_id
            )
            logger.info(f"Connected to Firestore: {self.settings.gcp_project_id}")
        except ImportError:
            logger.warning("google-cloud-firestore not installed, using mock client")
        except Exception as e:
            logger.error(f"Failed to connect to Firestore: {e}")
    
    def _collection(self, name: str):
        """Get collection reference with prefix."""
        if self._client:
            return self._client.collection(
                f"{self.settings.firestore_collection_prefix}_{name}"
            )
        return None
    
    def _init_mock_data(self) -> Dict[str, List[Any]]:
        """Initialize mock data for development."""
        return {
            "jobs": [
                {
                    "id": f"job-{i}",
                    "job_type": JobType.SCRAPE.value if i % 3 == 0 else JobType.EXTRACT_FEATURES.value,
                    "source": ScraperSource.META_AD_LIBRARY.value if i % 2 == 0 else ScraperSource.GOOGLE_ADS_TRANSPARENCY.value,
                    "status": [JobStatus.COMPLETED.value, JobStatus.PENDING.value, JobStatus.IN_PROGRESS.value, JobStatus.FAILED.value][i % 4],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "assets_processed": (i + 1) * 10 if i % 4 == 0 else 0,
                    "payload": {"query": "test", "max_items": 100},
                    "priority": i % 3,
                    "retry_count": 0 if i % 4 != 3 else 2,
                    "error_message": "Rate limit exceeded" if i % 4 == 3 else None,
                }
                for i in range(50)
            ],
            "assets": [
                {
                    "id": f"asset-{i}",
                    "source": [ScraperSource.META_AD_LIBRARY.value, ScraperSource.GOOGLE_ADS_TRANSPARENCY.value][i % 2],
                    "source_url": f"https://example.com/ad/{i}",
                    "image_url": f"https://picsum.photos/seed/{i}/400/300",
                    "asset_type": "image",
                    "advertiser_name": f"Advertiser {i % 10}",
                    "title": f"Creative Ad {i}",
                    "industry": list(IndustryCategory)[i % len(IndustryCategory)].value,
                    "features": {
                        "layout_type": ["hero", "grid", "split", "minimal"][i % 4],
                        "focal_point": ["product", "person", "text", "logo"][i % 4],
                        "visual_complexity": ["simple", "moderate", "complex"][i % 3],
                        "tone": ["professional", "playful", "urgent", "friendly"][i % 4],
                        "dominant_colors": [
                            {"hex": "#2980b9", "percentage": 0.4},
                            {"hex": "#ffffff", "percentage": 0.3},
                            {"hex": "#e74c3c", "percentage": 0.2},
                        ],
                        "cta": {
                            "detected": True,
                            "type": ["shop_now", "learn_more", "sign_up"][i % 3],
                            "text": ["Shop Now", "Learn More", "Sign Up"][i % 3],
                            "prominence": 0.8
                        },
                        "quality_score": 0.7 + (i % 30) / 100,
                        "has_logo": i % 3 == 0,
                        "has_human_face": i % 4 == 1,
                        "has_product": i % 2 == 0,
                    },
                    "reverse_prompt": f"Advertisement creative: {'hero' if i % 4 == 0 else 'split'} layout, professional tone, blue and white color palette, prominent CTA button saying 'Shop Now', high quality, clean composition" if i % 2 == 0 else None,
                    "negative_prompt": "blurry, low quality, amateur, cluttered" if i % 2 == 0 else None,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
                for i in range(100)
            ],
        }
    
    # ==========================================================================
    # Job Operations
    # ==========================================================================
    
    async def get_jobs(
        self,
        status: Optional[JobStatus] = None,
        job_type: Optional[JobType] = None,
        source: Optional[ScraperSource] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Job], int]:
        """Get jobs with optional filters."""
        if self._client:
            query = self._collection("jobs")
            if status:
                query = query.where("status", "==", status.value)
            if job_type:
                query = query.where("job_type", "==", job_type.value)
            if source:
                query = query.where("source", "==", source.value)
            
            query = query.order_by("created_at", direction="DESCENDING")
            query = query.limit(page_size).offset((page - 1) * page_size)
            
            docs = await query.get()
            jobs = [Job(id=doc.id, **doc.to_dict()) for doc in docs]
            
            # Get total count
            count_query = self._collection("jobs")
            if status:
                count_query = count_query.where("status", "==", status.value)
            total = len(await count_query.select([]).get())
            
            return jobs, total
        
        # Mock implementation
        jobs = self._mock_data["jobs"]
        if status:
            jobs = [j for j in jobs if j["status"] == status.value]
        if job_type:
            jobs = [j for j in jobs if j["job_type"] == job_type.value]
        if source:
            jobs = [j for j in jobs if j.get("source") == source.value]
        
        total = len(jobs)
        start = (page - 1) * page_size
        end = start + page_size
        page_jobs = jobs[start:end]
        
        return [Job(**j) for j in page_jobs], total
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a single job by ID."""
        if self._client:
            doc = await self._collection("jobs").document(job_id).get()
            if doc.exists:
                return Job(id=doc.id, **doc.to_dict())
            return None
        
        # Mock implementation
        for job in self._mock_data["jobs"]:
            if job["id"] == job_id:
                return Job(**job)
        return None
    
    async def create_job(self, job_data: Dict[str, Any]) -> str:
        """Create a new job."""
        import uuid
        job_id = str(uuid.uuid4())
        
        job_data["id"] = job_id
        job_data["created_at"] = datetime.utcnow().isoformat()
        job_data["updated_at"] = datetime.utcnow().isoformat()
        job_data["status"] = JobStatus.PENDING.value
        
        if self._client:
            await self._collection("jobs").document(job_id).set(job_data)
        else:
            self._mock_data["jobs"].insert(0, job_data)
        
        return job_id
    
    async def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update job fields."""
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        if self._client:
            doc_ref = self._collection("jobs").document(job_id)
            await doc_ref.update(updates)
            return True
        
        # Mock implementation
        for i, job in enumerate(self._mock_data["jobs"]):
            if job["id"] == job_id:
                self._mock_data["jobs"][i].update(updates)
                return True
        return False
    
    async def get_job_counts_by_status(self) -> Dict[str, int]:
        """Get job counts grouped by status."""
        counts = {status.value: 0 for status in JobStatus}
        
        if self._client:
            docs = await self._collection("jobs").get()
            for doc in docs:
                status = doc.to_dict().get("status", "pending")
                counts[status] = counts.get(status, 0) + 1
        else:
            for job in self._mock_data["jobs"]:
                status = job.get("status", "pending")
                counts[status] = counts.get(status, 0) + 1
        
        return counts
    
    # ==========================================================================
    # Asset Operations
    # ==========================================================================
    
    async def get_assets(
        self,
        filters: Optional[AssetFilterParams] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Asset], int]:
        """Get assets with optional filters."""
        if self._client:
            query = self._collection("assets")
            
            if filters:
                if filters.industry:
                    query = query.where("industry", "==", filters.industry.value)
                if filters.source:
                    query = query.where("source", "==", filters.source.value)
                if filters.has_prompt is not None:
                    if filters.has_prompt:
                        query = query.where("reverse_prompt", "!=", None)
                    else:
                        query = query.where("reverse_prompt", "==", None)
            
            query = query.order_by("created_at", direction="DESCENDING")
            query = query.limit(page_size).offset((page - 1) * page_size)
            
            docs = await query.get()
            assets = [Asset(id=doc.id, **doc.to_dict()) for doc in docs]
            
            # Total count
            count_query = self._collection("assets")
            if filters and filters.industry:
                count_query = count_query.where("industry", "==", filters.industry.value)
            total = len(await count_query.select([]).get())
            
            return assets, total
        
        # Mock implementation
        assets = self._mock_data["assets"]
        
        if filters:
            if filters.industry:
                assets = [a for a in assets if a.get("industry") == filters.industry.value]
            if filters.source:
                assets = [a for a in assets if a.get("source") == filters.source.value]
            if filters.has_prompt is not None:
                if filters.has_prompt:
                    assets = [a for a in assets if a.get("reverse_prompt")]
                else:
                    assets = [a for a in assets if not a.get("reverse_prompt")]
            if filters.cta_type:
                assets = [
                    a for a in assets 
                    if a.get("features", {}).get("cta", {}).get("type") == filters.cta_type
                ]
            if filters.focal_point:
                assets = [
                    a for a in assets 
                    if a.get("features", {}).get("focal_point") == filters.focal_point
                ]
            if filters.tone:
                assets = [
                    a for a in assets 
                    if a.get("features", {}).get("tone") == filters.tone
                ]
            if filters.search:
                search_lower = filters.search.lower()
                assets = [
                    a for a in assets
                    if search_lower in (a.get("title") or "").lower()
                    or search_lower in (a.get("advertiser_name") or "").lower()
                ]
        
        total = len(assets)
        start = (page - 1) * page_size
        end = start + page_size
        page_assets = assets[start:end]
        
        return [Asset(**a) for a in page_assets], total
    
    async def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get a single asset by ID."""
        if self._client:
            doc = await self._collection("assets").document(asset_id).get()
            if doc.exists:
                return Asset(id=doc.id, **doc.to_dict())
            return None
        
        # Mock implementation
        for asset in self._mock_data["assets"]:
            if asset["id"] == asset_id:
                return Asset(**asset)
        return None
    
    async def update_asset(self, asset_id: str, updates: Dict[str, Any]) -> bool:
        """Update asset fields."""
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        if self._client:
            doc_ref = self._collection("assets").document(asset_id)
            await doc_ref.update(updates)
            return True
        
        # Mock implementation
        for i, asset in enumerate(self._mock_data["assets"]):
            if asset["id"] == asset_id:
                self._mock_data["assets"][i].update(updates)
                return True
        return False
    
    async def get_industry_distribution(self) -> Dict[str, int]:
        """Get asset counts by industry."""
        distribution = {industry.value: 0 for industry in IndustryCategory}
        
        if self._client:
            docs = await self._collection("assets").get()
            for doc in docs:
                industry = doc.to_dict().get("industry", "other")
                distribution[industry] = distribution.get(industry, 0) + 1
        else:
            for asset in self._mock_data["assets"]:
                industry = asset.get("industry", "other")
                distribution[industry] = distribution.get(industry, 0) + 1
        
        return distribution
    
    async def get_source_distribution(self) -> Dict[str, int]:
        """Get asset counts by source."""
        distribution = {source.value: 0 for source in ScraperSource}
        
        if self._client:
            docs = await self._collection("assets").get()
            for doc in docs:
                source = doc.to_dict().get("source")
                if source:
                    distribution[source] = distribution.get(source, 0) + 1
        else:
            for asset in self._mock_data["assets"]:
                source = asset.get("source")
                if source:
                    distribution[source] = distribution.get(source, 0) + 1
        
        return distribution
    
    async def get_cta_distribution(self) -> Dict[str, int]:
        """Get asset counts by CTA type."""
        distribution = {}
        
        assets = self._mock_data["assets"]
        for asset in assets:
            cta = asset.get("features", {}).get("cta", {})
            cta_type = cta.get("type", "none") if cta.get("detected") else "none"
            distribution[cta_type] = distribution.get(cta_type, 0) + 1
        
        return distribution


@lru_cache()
def get_firestore_service() -> FirestoreService:
    """Get cached FirestoreService instance."""
    return FirestoreService(get_settings())

