"""
Job Service for Dashboard

Handles job queue operations, triggering, and control.
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from functools import lru_cache

import httpx

from ..config import get_settings, Settings
from ..models import (
    Job, JobCreate, JobStatus, JobType, ScraperSource,
    JobControlRequest, JobControlResponse, ScraperTriggerRequest,
    ScraperTriggerResponse, QueueMetrics
)
from .firestore_service import FirestoreService, get_firestore_service

logger = logging.getLogger(__name__)


class JobService:
    """Service for job queue operations."""
    
    def __init__(self, settings: Settings, firestore: FirestoreService):
        self.settings = settings
        self.firestore = firestore
        self._pubsub_publisher = None
    
    @property
    def pubsub_publisher(self):
        """Get Pub/Sub publisher (lazy initialization)."""
        if self._pubsub_publisher is None:
            self._initialize_pubsub()
        return self._pubsub_publisher
    
    def _initialize_pubsub(self):
        """Initialize Pub/Sub publisher."""
        if not self.settings.gcp_project_id:
            logger.warning("No GCP project ID, Pub/Sub disabled")
            return
        
        try:
            from google.cloud import pubsub_v1
            self._pubsub_publisher = pubsub_v1.PublisherClient()
            logger.info("Initialized Pub/Sub publisher")
        except ImportError:
            logger.warning("google-cloud-pubsub not installed")
        except Exception as e:
            logger.error(f"Failed to initialize Pub/Sub: {e}")
    
    async def create_job(self, job_create: JobCreate) -> Job:
        """Create and queue a new job."""
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        job_data = {
            "id": job_id,
            "job_type": job_create.job_type.value,
            "source": job_create.source.value if job_create.source else None,
            "status": JobStatus.PENDING.value,
            "payload": {
                **job_create.payload,
                "query": job_create.query,
                "filters": job_create.filters,
                "max_items": job_create.max_items,
            },
            "priority": job_create.priority,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "retry_count": 0,
            "max_retries": 3,
            "assets_processed": 0,
        }
        
        # Store in Firestore
        await self.firestore.create_job(job_data)
        
        # Publish to Pub/Sub
        await self._publish_job(job_data)
        
        logger.info(f"Created job: {job_id}")
        return Job(**job_data)
    
    async def _publish_job(self, job_data: Dict[str, Any]) -> None:
        """Publish job to Pub/Sub queue."""
        if not self.pubsub_publisher:
            logger.debug("Pub/Sub not available, skipping publish")
            return
        
        try:
            import json
            
            topic_path = self.pubsub_publisher.topic_path(
                self.settings.gcp_project_id,
                self.settings.pubsub_topic
            )
            
            message_data = json.dumps(job_data).encode('utf-8')
            
            future = self.pubsub_publisher.publish(
                topic_path,
                data=message_data,
                job_id=job_data["id"],
                job_type=job_data["job_type"]
            )
            
            # Don't block, just log
            logger.debug(f"Published job to Pub/Sub: {job_data['id']}")
            
        except Exception as e:
            logger.error(f"Failed to publish job to Pub/Sub: {e}")
    
    async def control_jobs(self, request: JobControlRequest) -> JobControlResponse:
        """Control multiple jobs (start, stop, pause, resume, retry, cancel)."""
        affected = []
        action = request.action
        
        for job_id in request.job_ids:
            job = await self.firestore.get_job(job_id)
            if not job:
                continue
            
            new_status = None
            
            if action == "start" and job.status == JobStatus.PENDING:
                new_status = JobStatus.IN_PROGRESS
            elif action == "stop" and job.status == JobStatus.IN_PROGRESS:
                new_status = JobStatus.CANCELLED
            elif action == "pause" and job.status == JobStatus.IN_PROGRESS:
                new_status = JobStatus.PAUSED
            elif action == "resume" and job.status == JobStatus.PAUSED:
                new_status = JobStatus.IN_PROGRESS
            elif action == "retry" and job.status == JobStatus.FAILED:
                new_status = JobStatus.PENDING
            elif action == "cancel":
                new_status = JobStatus.CANCELLED
            
            if new_status:
                await self.firestore.update_job(job_id, {"status": new_status.value})
                
                # Re-publish for retry
                if action == "retry":
                    job_dict = job.model_dump()
                    job_dict["status"] = new_status.value
                    job_dict["retry_count"] = job.retry_count + 1
                    await self._publish_job(job_dict)
                
                affected.append(job_id)
        
        return JobControlResponse(
            success=len(affected) > 0,
            affected_jobs=affected,
            message=f"{action.capitalize()}ed {len(affected)} job(s)"
        )
    
    async def trigger_scraping(
        self, 
        request: ScraperTriggerRequest
    ) -> ScraperTriggerResponse:
        """Trigger scraping jobs for specified sources."""
        job_ids = []
        
        for source in request.sources:
            job_create = JobCreate(
                job_type=JobType.SCRAPE,
                source=source,
                payload={},
                query=request.query,
                filters=request.filters,
                max_items=request.max_items_per_source,
                priority=1
            )
            
            job = await self.create_job(job_create)
            job_ids.append(job.id)
        
        # Optionally call the agent service
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.settings.agent_service_url}/trigger",
                    json={
                        "sources": [s.value for s in request.sources],
                        "industries": [i.value for i in request.industries] if request.industries else None,
                        "max_items_per_source": request.max_items_per_source,
                    }
                )
                if response.status_code == 200:
                    logger.info("Successfully triggered agent service")
        except Exception as e:
            logger.warning(f"Failed to trigger agent service: {e}")
        
        return ScraperTriggerResponse(
            triggered=True,
            job_ids=job_ids,
            message=f"Triggered {len(job_ids)} scraping jobs for {len(request.sources)} sources"
        )
    
    async def get_queue_metrics(self) -> QueueMetrics:
        """Get current queue metrics."""
        counts = await self.firestore.get_job_counts_by_status()
        
        # Calculate totals
        total = sum(counts.values())
        completed = counts.get(JobStatus.COMPLETED.value, 0)
        failed = counts.get(JobStatus.FAILED.value, 0)
        
        # Calculate jobs per minute (mock for now)
        jobs_per_minute = completed / 60 if completed > 0 else 0
        
        return QueueMetrics(
            total_jobs=total,
            pending_jobs=counts.get(JobStatus.PENDING.value, 0),
            in_progress_jobs=counts.get(JobStatus.IN_PROGRESS.value, 0),
            completed_jobs=completed,
            failed_jobs=failed,
            dead_letter_jobs=0,  # Would come from DLQ subscription
            avg_processing_time_seconds=5.2,  # Mock value
            jobs_per_minute=jobs_per_minute
        )
    
    async def retry_failed_jobs(self, max_jobs: int = 10) -> int:
        """Retry all failed jobs up to a limit."""
        jobs, _ = await self.firestore.get_jobs(
            status=JobStatus.FAILED,
            page_size=max_jobs
        )
        
        retried = 0
        for job in jobs:
            if job.retry_count < job.max_retries:
                await self.firestore.update_job(
                    job.id, 
                    {
                        "status": JobStatus.PENDING.value,
                        "retry_count": job.retry_count + 1,
                        "error_message": None
                    }
                )
                retried += 1
        
        return retried


@lru_cache()
def get_job_service() -> JobService:
    """Get cached JobService instance."""
    return JobService(get_settings(), get_firestore_service())

