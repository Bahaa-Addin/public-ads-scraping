"""
Job Queue Management for Agentic Ads Platform

Handles job distribution, retries, and dead-letter queue management
using Google Cloud Pub/Sub or a local queue for development.
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"


class JobType(Enum):
    """Types of jobs in the pipeline."""
    SCRAPE = "scrape"
    EXTRACT_FEATURES = "extract_features"
    GENERATE_PROMPT = "generate_prompt"
    CLASSIFY_INDUSTRY = "classify_industry"
    STORE_ASSET = "store_asset"
    BATCH_PROCESS = "batch_process"


@dataclass
class Job:
    """Represents a single job in the queue."""
    id: str
    job_type: JobType
    payload: Dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    source: Optional[str] = None
    priority: int = 0  # Higher = more priority
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for serialization."""
        return {
            "id": self.id,
            "job_type": self.job_type.value,
            "payload": self.payload,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "source": self.source,
            "priority": self.priority,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        """Create job from dictionary."""
        return cls(
            id=data["id"],
            job_type=JobType(data["job_type"]),
            payload=data["payload"],
            status=JobStatus(data.get("status", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            error_message=data.get("error_message"),
            source=data.get("source"),
            priority=data.get("priority", 0),
        )


@dataclass
class JobMetrics:
    """Metrics for job queue monitoring."""
    total_jobs: int = 0
    pending_jobs: int = 0
    in_progress_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    dead_letter_jobs: int = 0
    avg_processing_time_seconds: float = 0.0
    jobs_per_minute: float = 0.0


class JobQueue:
    """
    Job queue manager supporting both Pub/Sub and local queues.
    
    In production, uses Google Cloud Pub/Sub for distributed job management.
    In development, uses an in-memory queue for testing.
    """
    
    def __init__(
        self,
        project_id: str,
        topic_name: str,
        subscription_name: str,
        use_local_queue: bool = False,
        dlq_topic_name: Optional[str] = None
    ):
        self.project_id = project_id
        self.topic_name = topic_name
        self.subscription_name = subscription_name
        self.dlq_topic_name = dlq_topic_name or f"{topic_name}-dlq"
        self.use_local_queue = use_local_queue
        
        # Local queue for development/testing
        self._local_queue: deque = deque()
        self._in_progress: Dict[str, Job] = {}
        self._completed: List[Job] = []
        self._failed: List[Job] = []
        
        # Pub/Sub clients (initialized lazily)
        self._publisher = None
        self._subscriber = None
        self._subscription_path = None
        
        # Metrics
        self._metrics = JobMetrics()
        self._processing_times: List[float] = []
        
        # Handlers
        self._handlers: Dict[JobType, Callable] = {}
        
    async def initialize(self) -> None:
        """Initialize the job queue connections."""
        if self.use_local_queue:
            logger.info("Using local in-memory job queue")
            return
            
        try:
            from google.cloud import pubsub_v1
            
            self._publisher = pubsub_v1.PublisherClient()
            self._subscriber = pubsub_v1.SubscriberClient()
            
            self._topic_path = self._publisher.topic_path(
                self.project_id, self.topic_name
            )
            self._subscription_path = self._subscriber.subscription_path(
                self.project_id, self.subscription_name
            )
            self._dlq_topic_path = self._publisher.topic_path(
                self.project_id, self.dlq_topic_name
            )
            
            logger.info(f"Initialized Pub/Sub queue: {self._topic_path}")
            
        except ImportError:
            logger.warning("google-cloud-pubsub not installed, falling back to local queue")
            self.use_local_queue = True
        except Exception as e:
            logger.error(f"Failed to initialize Pub/Sub: {e}")
            raise
            
    async def close(self) -> None:
        """Close queue connections."""
        if self._subscriber:
            self._subscriber.close()
        if self._publisher:
            # Publisher doesn't have a close method, but we can clear reference
            self._publisher = None
        logger.info("Job queue connections closed")
        
    def register_handler(self, job_type: JobType, handler: Callable) -> None:
        """Register a handler for a specific job type."""
        self._handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type.value}")
        
    async def enqueue(self, job: Job) -> str:
        """Add a job to the queue."""
        job.id = job.id or str(uuid.uuid4())
        job.status = JobStatus.PENDING
        job.created_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        
        if self.use_local_queue:
            self._local_queue.append(job)
            self._metrics.pending_jobs += 1
        else:
            await self._publish_to_pubsub(job)
            
        self._metrics.total_jobs += 1
        logger.debug(f"Enqueued job: {job.id} ({job.job_type.value})")
        
        return job.id
        
    async def enqueue_batch(self, jobs: List[Job]) -> List[str]:
        """Add multiple jobs to the queue."""
        job_ids = []
        for job in jobs:
            job_id = await self.enqueue(job)
            job_ids.append(job_id)
        return job_ids
        
    async def dequeue(self, timeout_seconds: float = 10.0) -> Optional[Job]:
        """Get the next job from the queue."""
        if self.use_local_queue:
            if self._local_queue:
                job = self._local_queue.popleft()
                job.status = JobStatus.IN_PROGRESS
                job.started_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                self._in_progress[job.id] = job
                self._metrics.pending_jobs -= 1
                self._metrics.in_progress_jobs += 1
                return job
            return None
        else:
            return await self._pull_from_pubsub(timeout_seconds)
            
    async def complete(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark a job as completed."""
        job = self._in_progress.pop(job_id, None)
        if job:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            self._completed.append(job)
            self._metrics.in_progress_jobs -= 1
            self._metrics.completed_jobs += 1
            
            # Track processing time
            if job.started_at:
                processing_time = (job.completed_at - job.started_at).total_seconds()
                self._processing_times.append(processing_time)
                self._update_avg_processing_time()
                
            logger.debug(f"Completed job: {job_id}")
            
    async def fail(self, job_id: str, error: str, retry: bool = True) -> None:
        """Mark a job as failed, optionally retrying."""
        job = self._in_progress.pop(job_id, None)
        if not job:
            logger.warning(f"Job not found for failure: {job_id}")
            return
            
        job.error_message = error
        job.updated_at = datetime.utcnow()
        
        if retry and job.retry_count < job.max_retries:
            job.retry_count += 1
            job.status = JobStatus.RETRYING
            
            # Exponential backoff
            delay = min(2 ** job.retry_count, 60)
            await asyncio.sleep(delay)
            
            await self.enqueue(job)
            logger.info(f"Retrying job {job_id} (attempt {job.retry_count}/{job.max_retries})")
        else:
            job.status = JobStatus.DEAD_LETTER
            await self._send_to_dlq(job)
            self._failed.append(job)
            self._metrics.in_progress_jobs -= 1
            self._metrics.dead_letter_jobs += 1
            logger.error(f"Job {job_id} moved to dead letter queue: {error}")
            
    async def _publish_to_pubsub(self, job: Job) -> None:
        """Publish a job to Pub/Sub."""
        if not self._publisher:
            raise RuntimeError("Pub/Sub publisher not initialized")
            
        message_data = json.dumps(job.to_dict()).encode('utf-8')
        
        future = self._publisher.publish(
            self._topic_path,
            data=message_data,
            job_id=job.id,
            job_type=job.job_type.value
        )
        
        # Wait for publish to complete
        await asyncio.get_event_loop().run_in_executor(None, future.result)
        
    async def _pull_from_pubsub(self, timeout_seconds: float) -> Optional[Job]:
        """Pull a job from Pub/Sub subscription."""
        if not self._subscriber:
            raise RuntimeError("Pub/Sub subscriber not initialized")
            
        from google.cloud.pubsub_v1 import types
        
        response = self._subscriber.pull(
            request={
                "subscription": self._subscription_path,
                "max_messages": 1,
            },
            timeout=timeout_seconds
        )
        
        if not response.received_messages:
            return None
            
        message = response.received_messages[0]
        
        try:
            job_data = json.loads(message.message.data.decode('utf-8'))
            job = Job.from_dict(job_data)
            job.status = JobStatus.IN_PROGRESS
            job.started_at = datetime.utcnow()
            
            # Acknowledge the message
            self._subscriber.acknowledge(
                request={
                    "subscription": self._subscription_path,
                    "ack_ids": [message.ack_id],
                }
            )
            
            self._in_progress[job.id] = job
            return job
            
        except Exception as e:
            logger.error(f"Failed to process Pub/Sub message: {e}")
            return None
            
    async def _send_to_dlq(self, job: Job) -> None:
        """Send a failed job to the dead letter queue."""
        if self.use_local_queue:
            self._failed.append(job)
            return
            
        if self._publisher:
            message_data = json.dumps(job.to_dict()).encode('utf-8')
            future = self._publisher.publish(
                self._dlq_topic_path,
                data=message_data,
                job_id=job.id,
                failure_reason=job.error_message or "Unknown"
            )
            await asyncio.get_event_loop().run_in_executor(None, future.result)
            
    def _update_avg_processing_time(self) -> None:
        """Update average processing time metric."""
        if self._processing_times:
            # Keep last 1000 samples
            if len(self._processing_times) > 1000:
                self._processing_times = self._processing_times[-1000:]
            self._metrics.avg_processing_time_seconds = (
                sum(self._processing_times) / len(self._processing_times)
            )
            
    def get_metrics(self) -> JobMetrics:
        """Get current queue metrics."""
        return self._metrics
        
    def get_queue_size(self) -> int:
        """Get current queue size."""
        if self.use_local_queue:
            return len(self._local_queue)
        return self._metrics.pending_jobs
        
    async def create_scrape_job(
        self,
        source: str,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        priority: int = 0
    ) -> str:
        """Create and enqueue a scraping job."""
        job = Job(
            id=str(uuid.uuid4()),
            job_type=JobType.SCRAPE,
            payload={
                "source": source,
                "query": query,
                "filters": filters or {},
            },
            source=source,
            priority=priority,
        )
        return await self.enqueue(job)
        
    async def create_feature_extraction_job(
        self,
        asset_id: str,
        asset_url: str,
        asset_type: str = "image"
    ) -> str:
        """Create and enqueue a feature extraction job."""
        job = Job(
            id=str(uuid.uuid4()),
            job_type=JobType.EXTRACT_FEATURES,
            payload={
                "asset_id": asset_id,
                "asset_url": asset_url,
                "asset_type": asset_type,
            },
        )
        return await self.enqueue(job)
        
    async def create_prompt_generation_job(
        self,
        asset_id: str,
        features: Dict[str, Any],
        industry: Optional[str] = None
    ) -> str:
        """Create and enqueue a reverse-prompt generation job."""
        job = Job(
            id=str(uuid.uuid4()),
            job_type=JobType.GENERATE_PROMPT,
            payload={
                "asset_id": asset_id,
                "features": features,
                "industry": industry,
            },
        )
        return await self.enqueue(job)

