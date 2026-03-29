"""
Firestore Service for Dashboard

Provides data access layer for Firestore operations.
In local mode, reads from local JSON files instead of Firestore.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
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
        self._local_data: Dict[str, List[Any]] = {"jobs": [], "assets": []}
        
        # Initialize based on mode
        if self.settings.mode == "local":
            self._load_local_data()
        else:
            self._initialize_client()
    
    @property
    def client(self):
        """Get Firestore client (lazy initialization)."""
        if self._client is None and self.settings.mode != "local":
            self._initialize_client()
        return self._client
    
    def _get_data_path(self, filename: str) -> Path:
        """Get the full path to a data file."""
        # Handle relative and absolute paths
        data_dir = self.settings.data_dir
        if not os.path.isabs(data_dir):
            # Relative to the backend app directory
            backend_dir = Path(__file__).parent.parent.parent
            data_dir = backend_dir / data_dir
        return Path(data_dir) / filename
    
    def _load_local_data(self, force: bool = False):
        """
        Load data from local JSON files.
        
        In local mode, always reads fresh from disk to pick up changes
        from the Agent service.
        """
        # Load jobs
        jobs_path = self._get_data_path("db/jobs.json")
        if jobs_path.exists():
            try:
                with open(jobs_path, "r") as f:
                    self._local_data["jobs"] = json.load(f)
                if force:
                    logger.debug(f"Refreshed {len(self._local_data['jobs'])} jobs from {jobs_path}")
                else:
                    logger.info(f"Loaded {len(self._local_data['jobs'])} jobs from {jobs_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load jobs from {jobs_path}: {e}")
                self._local_data["jobs"] = []
        else:
            if not force:
                logger.info(f"Jobs file not found at {jobs_path}, starting with empty data")
            self._local_data["jobs"] = []
        
        # Load assets
        assets_path = self._get_data_path("db/assets.json")
        if assets_path.exists():
            try:
                with open(assets_path, "r") as f:
                    self._local_data["assets"] = json.load(f)
                if force:
                    logger.debug(f"Refreshed {len(self._local_data['assets'])} assets from {assets_path}")
                else:
                    logger.info(f"Loaded {len(self._local_data['assets'])} assets from {assets_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load assets from {assets_path}: {e}")
                self._local_data["assets"] = []
        else:
            if not force:
                logger.info(f"Assets file not found at {assets_path}, starting with empty data")
            self._local_data["assets"] = []
    
    def _refresh_data(self):
        """Refresh data from disk (for local mode)."""
        if self.settings.mode == "local":
            self._load_local_data(force=True)
    
    def _save_local_data(self, collection: str):
        """Save data to local JSON file."""
        if collection == "jobs":
            path = self._get_data_path("db/jobs.json")
        elif collection == "assets":
            path = self._get_data_path("db/assets.json")
        else:
            return
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(self._local_data[collection], f, indent=2, default=str)
            logger.debug(f"Saved {len(self._local_data[collection])} {collection} to {path}")
        except IOError as e:
            logger.error(f"Failed to save {collection} to {path}: {e}")
    
    def _initialize_client(self):
        """Initialize Firestore client."""
        if not self.settings.gcp_project_id:
            logger.warning("No GCP project ID, running in local mode")
            return
        
        try:
            from google.cloud import firestore
            self._client = firestore.AsyncClient(
                project=self.settings.gcp_project_id,
                database=self.settings.firestore_database_id
            )
            logger.info(f"Connected to Firestore: {self.settings.gcp_project_id}")
        except ImportError:
            logger.warning("google-cloud-firestore not installed, using local mode")
        except Exception as e:
            logger.error(f"Failed to connect to Firestore: {e}")
    
    def _collection(self, name: str):
        """Get collection reference with prefix."""
        if self._client:
            return self._client.collection(
                f"{self.settings.firestore_collection_prefix}_{name}"
            )
        return None
    
    def _is_local_mode(self) -> bool:
        """Check if running in local mode."""
        return self.settings.mode == "local" or self._client is None
    
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
        if not self._is_local_mode():
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
        
        # Local mode - read from JSON (refresh to pick up Agent updates)
        self._refresh_data()
        jobs = self._local_data["jobs"].copy()
        
        if status:
            jobs = [j for j in jobs if j.get("status") == status.value]
        if job_type:
            jobs = [j for j in jobs if j.get("job_type") == job_type.value]
        if source:
            jobs = [j for j in jobs if j.get("source") == source.value]
        
        # Sort by created_at descending
        jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        total = len(jobs)
        start = (page - 1) * page_size
        end = start + page_size
        page_jobs = jobs[start:end]
        
        return [Job(**j) for j in page_jobs], total
    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get a single job by ID."""
        if not self._is_local_mode():
            doc = await self._collection("jobs").document(job_id).get()
            if doc.exists:
                return Job(id=doc.id, **doc.to_dict())
            return None
        
        # Local mode - refresh to pick up Agent updates
        self._refresh_data()
        for job in self._local_data["jobs"]:
            if job.get("id") == job_id:
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
        
        if not self._is_local_mode():
            await self._collection("jobs").document(job_id).set(job_data)
        else:
            self._local_data["jobs"].insert(0, job_data)
            self._save_local_data("jobs")
        
        return job_id
    
    async def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update job fields."""
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        if not self._is_local_mode():
            doc_ref = self._collection("jobs").document(job_id)
            await doc_ref.update(updates)
            return True
        
        # Local mode
        for i, job in enumerate(self._local_data["jobs"]):
            if job.get("id") == job_id:
                self._local_data["jobs"][i].update(updates)
                self._save_local_data("jobs")
                return True
        return False
    
    async def get_job_counts_by_status(self) -> Dict[str, int]:
        """Get job counts grouped by status."""
        counts = {status.value: 0 for status in JobStatus}
        
        if not self._is_local_mode():
            docs = await self._collection("jobs").get()
            for doc in docs:
                status = doc.to_dict().get("status", "pending")
                counts[status] = counts.get(status, 0) + 1
        else:
            # Refresh data to pick up Agent updates
            self._refresh_data()
            for job in self._local_data["jobs"]:
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
        if not self._is_local_mode():
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
        
        # Local mode - refresh to pick up Agent updates
        self._refresh_data()
        assets = self._local_data["assets"].copy()
        
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
        
        # Sort by created_at descending
        assets.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        total = len(assets)
        start = (page - 1) * page_size
        end = start + page_size
        page_assets = assets[start:end]
        
        return [Asset(**a) for a in page_assets], total
    
    async def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get a single asset by ID."""
        if not self._is_local_mode():
            doc = await self._collection("assets").document(asset_id).get()
            if doc.exists:
                return Asset(id=doc.id, **doc.to_dict())
            return None
        
        # Local mode
        for asset in self._local_data["assets"]:
            if asset.get("id") == asset_id:
                return Asset(**asset)
        return None
    
    async def create_asset(self, asset_data: Dict[str, Any]) -> str:
        """Create a new asset."""
        import uuid
        asset_id = asset_data.get("id") or str(uuid.uuid4())
        
        asset_data["id"] = asset_id
        asset_data["created_at"] = asset_data.get("created_at") or datetime.utcnow().isoformat()
        asset_data["updated_at"] = datetime.utcnow().isoformat()
        
        if not self._is_local_mode():
            await self._collection("assets").document(asset_id).set(asset_data)
        else:
            self._local_data["assets"].insert(0, asset_data)
            self._save_local_data("assets")
        
        return asset_id
    
    async def update_asset(self, asset_id: str, updates: Dict[str, Any]) -> bool:
        """Update asset fields."""
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        if not self._is_local_mode():
            doc_ref = self._collection("assets").document(asset_id)
            await doc_ref.update(updates)
            return True
        
        # Local mode
        for i, asset in enumerate(self._local_data["assets"]):
            if asset.get("id") == asset_id:
                self._local_data["assets"][i].update(updates)
                self._save_local_data("assets")
                return True
        return False
    
    async def get_industry_distribution(self) -> Dict[str, int]:
        """Get asset counts by industry."""
        distribution = {industry.value: 0 for industry in IndustryCategory}
        
        if not self._is_local_mode():
            docs = await self._collection("assets").get()
            for doc in docs:
                industry = doc.to_dict().get("industry", "other")
                distribution[industry] = distribution.get(industry, 0) + 1
        else:
            for asset in self._local_data["assets"]:
                industry = asset.get("industry", "other")
                distribution[industry] = distribution.get(industry, 0) + 1
        
        return distribution
    
    async def get_source_distribution(self) -> Dict[str, int]:
        """Get asset counts by source."""
        distribution = {source.value: 0 for source in ScraperSource}
        
        if not self._is_local_mode():
            docs = await self._collection("assets").get()
            for doc in docs:
                source = doc.to_dict().get("source")
                if source:
                    distribution[source] = distribution.get(source, 0) + 1
        else:
            for asset in self._local_data["assets"]:
                source = asset.get("source")
                if source:
                    distribution[source] = distribution.get(source, 0) + 1
        
        return distribution
    
    async def get_cta_distribution(self) -> Dict[str, int]:
        """Get asset counts by CTA type."""
        distribution = {}
        
        assets = self._local_data["assets"] if self._is_local_mode() else []
        
        if not self._is_local_mode():
            docs = await self._collection("assets").get()
            assets = [doc.to_dict() for doc in docs]
        
        for asset in assets:
            cta = asset.get("features", {}).get("cta", {})
            cta_type = cta.get("type", "none") if cta.get("detected") else "none"
            distribution[cta_type] = distribution.get(cta_type, 0) + 1
        
        return distribution
    
    async def get_quality_distribution(self) -> Dict[str, int]:
        """Get asset counts by quality score ranges."""
        distribution = {
            "excellent": 0,  # 0.9+
            "good": 0,       # 0.7-0.89
            "fair": 0,       # 0.5-0.69
            "poor": 0,       # <0.5
        }
        
        assets = self._local_data["assets"] if self._is_local_mode() else []
        
        if not self._is_local_mode():
            docs = await self._collection("assets").get()
            assets = [doc.to_dict() for doc in docs]
        
        for asset in assets:
            score = asset.get("features", {}).get("quality_score", 0)
            if score >= 0.9:
                distribution["excellent"] += 1
            elif score >= 0.7:
                distribution["good"] += 1
            elif score >= 0.5:
                distribution["fair"] += 1
            else:
                distribution["poor"] += 1
        
        return distribution
    
    def reload_local_data(self):
        """Reload data from local files (useful after external updates)."""
        if self._is_local_mode():
            self._load_local_data()


@lru_cache()
def get_firestore_service() -> FirestoreService:
    """Get cached FirestoreService instance."""
    return FirestoreService(get_settings())
