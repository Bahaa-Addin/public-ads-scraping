"""
Pub/Sub Queue Adapter

Implements QueueInterface using Google Cloud Pub/Sub.
CLOUD MODE ONLY.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from agent.interfaces.queue import (
    QueueInterface,
    JobData,
    JobStatus,
    JobType,
    QueueMetrics,
)

logger = logging.getLogger(__name__)


class PubSubQueue(QueueInterface):
    """
    Google Cloud Pub/Sub queue implementation.
    
    Uses:
    - Main topic for job publishing
    - Subscription for job processing
    - Dead letter topic for failed jobs
    
    CLOUD MODE ONLY - requires GCP credentials.
    """
    
    def __init__(
        self,
        project_id: str,
        topic_name: str = "creative-ads-jobs",
        subscription_name: str = "creative-ads-jobs-sub",
        dlq_topic_name: Optional[str] = None,
        max_retries: int = 3,
    ):
        self._validate_mode()
        
        self.project_id = project_id
        self.topic_name = topic_name
        self.subscription_name = subscription_name
        self.dlq_topic_name = dlq_topic_name or f"{topic_name}-dlq"
        self.max_retries = max_retries
        
        self._publisher = None
        self._subscriber = None
        self._topic_path = None
        self._subscription_path = None
        self._dlq_topic_path = None
        
        # Handlers and metrics
        self._handlers: Dict[JobType, Callable] = {}
        self._metrics = QueueMetrics()
        self._in_progress: Dict[str, JobData] = {}
        self._processing_times: List[float] = []
        
    def _validate_mode(self) -> None:
        """Validate that we're in cloud mode."""
        mode = os.environ.get("MODE", "local").lower()
        if mode != "cloud":
            raise RuntimeError(
                "PubSubQueue is only available in cloud mode. "
                "Set MODE=cloud to use cloud adapters, or use LocalQueue for local development."
            )
    
    async def initialize(self) -> None:
        """Initialize Pub/Sub connections."""
        from google.cloud import pubsub_v1
        
        self._publisher = pubsub_v1.PublisherClient()
        self._subscriber = pubsub_v1.SubscriberClient()
        
        self._topic_path = self._publisher.topic_path(self.project_id, self.topic_name)
        self._subscription_path = self._subscriber.subscription_path(
            self.project_id, self.subscription_name
        )
        self._dlq_topic_path = self._publisher.topic_path(self.project_id, self.dlq_topic_name)
        
        logger.info(f"Initialized Pub/Sub queue: {self._topic_path}")
    
    async def close(self) -> None:
        """Close Pub/Sub connections."""
        if self._subscriber:
            self._subscriber.close()
        logger.info("Pub/Sub queue connections closed")
    
    async def health_check(self) -> bool:
        """Check if queue is healthy."""
        try:
            # Check if topic exists
            self._publisher.get_topic(request={"topic": self._topic_path})
            return True
        except Exception as e:
            logger.error(f"Pub/Sub health check failed: {e}")
            return False
    
    def register_handler(self, job_type: JobType, handler: Callable) -> None:
        """Register a handler for a specific job type."""
        self._handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type.value}")
    
    async def enqueue(self, job: JobData) -> str:
        """Add a job to the queue."""
        if not job.id:
            job.id = str(uuid.uuid4())
        
        job.status = JobStatus.PENDING
        job.created_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        
        message_data = json.dumps(job.to_dict()).encode('utf-8')
        
        future = self._publisher.publish(
            self._topic_path,
            data=message_data,
            job_id=job.id,
            job_type=job.job_type.value,
            priority=str(job.priority)
        )
        
        # Wait for publish to complete
        await asyncio.get_event_loop().run_in_executor(None, future.result)
        
        self._metrics.total_jobs += 1
        self._metrics.pending_jobs += 1
        
        logger.debug(f"Enqueued job to Pub/Sub: {job.id} ({job.job_type.value})")
        
        return job.id
    
    async def enqueue_batch(self, jobs: List[JobData]) -> List[str]:
        """Add multiple jobs to the queue."""
        job_ids = []
        for job in jobs:
            job_id = await self.enqueue(job)
            job_ids.append(job_id)
        return job_ids
    
    async def dequeue(self, timeout_seconds: float = 10.0) -> Optional[JobData]:
        """Get the next job from the queue."""
        try:
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
            
            job_data = json.loads(message.message.data.decode('utf-8'))
            job = JobData.from_dict(job_data)
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
            self._metrics.pending_jobs -= 1
            self._metrics.in_progress_jobs += 1
            
            return job
            
        except Exception as e:
            logger.error(f"Failed to dequeue from Pub/Sub: {e}")
            return None
    
    async def complete(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark a job as completed."""
        job = self._in_progress.pop(job_id, None)
        
        if job:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            
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
            
            # Re-enqueue
            await self.enqueue(job)
            self._metrics.in_progress_jobs -= 1
            
            logger.info(f"Retrying job {job_id} (attempt {job.retry_count}/{job.max_retries})")
        else:
            job.status = JobStatus.DEAD_LETTER
            await self._send_to_dlq(job)
            
            self._metrics.in_progress_jobs -= 1
            self._metrics.failed_jobs += 1
            self._metrics.dead_letter_jobs += 1
            
            logger.error(f"Job {job_id} moved to dead letter queue: {error}")
    
    async def _send_to_dlq(self, job: JobData) -> None:
        """Send a failed job to the dead letter queue."""
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
            if len(self._processing_times) > 1000:
                self._processing_times = self._processing_times[-1000:]
            self._metrics.avg_processing_time_seconds = (
                sum(self._processing_times) / len(self._processing_times)
            )
    
    def get_metrics(self) -> QueueMetrics:
        """Get current queue metrics."""
        return self._metrics
    
    def get_queue_size(self) -> int:
        """Get current queue size (approximate for Pub/Sub)."""
        return self._metrics.pending_jobs
    
    async def create_scrape_job(
        self,
        source: str,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        priority: int = 0
    ) -> str:
        """Create and enqueue a scraping job."""
        job = JobData(
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
        job = JobData(
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
        job = JobData(
            id=str(uuid.uuid4()),
            job_type=JobType.GENERATE_PROMPT,
            payload={
                "asset_id": asset_id,
                "features": features,
                "industry": industry,
            },
        )
        return await self.enqueue(job)

