"""
Local Queue Adapter

Implements QueueInterface using an in-memory queue.
Emulates Google Cloud Pub/Sub for local development.
"""

import asyncio
import logging
import uuid
from collections import deque
from dataclasses import dataclass
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


class LocalQueue(QueueInterface):
    """
    In-memory queue implementation for local development.
    
    Emulates Google Cloud Pub/Sub behavior:
    - Priority queue with FIFO within same priority
    - Dead letter queue for failed jobs
    - Retry with exponential backoff
    """
    
    def __init__(
        self,
        max_queue_size: int = 10000,
        max_retries: int = 3
    ):
        self.max_queue_size = max_queue_size
        self.max_retries = max_retries
        
        # Queue storage
        self._queue: deque = deque()
        self._in_progress: Dict[str, JobData] = {}
        self._completed: List[JobData] = []
        self._failed: List[JobData] = []
        self._dead_letter: List[JobData] = []
        
        # Handlers
        self._handlers: Dict[JobType, Callable] = {}
        
        # Metrics
        self._metrics = QueueMetrics()
        self._processing_times: List[float] = []
        
        # Locks for thread safety
        self._lock = asyncio.Lock()
        
    async def initialize(self) -> None:
        """Initialize the local queue."""
        logger.info("Initialized local in-memory queue")
    
    async def close(self) -> None:
        """Close the queue (no-op for local)."""
        # Clear queues
        self._queue.clear()
        self._in_progress.clear()
        logger.info("Local queue closed")
    
    async def health_check(self) -> bool:
        """Check if queue is healthy."""
        return len(self._queue) < self.max_queue_size
    
    def register_handler(self, job_type: JobType, handler: Callable) -> None:
        """Register a handler for a specific job type."""
        self._handlers[job_type] = handler
        logger.info(f"Registered handler for job type: {job_type.value}")
    
    async def enqueue(self, job: JobData) -> str:
        """Add a job to the queue."""
        async with self._lock:
            # Generate ID if not set
            if not job.id:
                job.id = str(uuid.uuid4())
            
            job.status = JobStatus.PENDING
            job.created_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            
            # Check queue capacity
            if len(self._queue) >= self.max_queue_size:
                raise RuntimeError("Queue is at capacity")
            
            # Insert by priority (higher priority = earlier in queue)
            # Simple approach: append and sort
            self._queue.append(job)
            
            # Update metrics
            self._metrics.total_jobs += 1
            self._metrics.pending_jobs += 1
            
            logger.debug(f"Enqueued job: {job.id} ({job.job_type.value})")
            
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
        async with self._lock:
            if not self._queue:
                return None
            
            # Get highest priority job (sort by priority descending)
            sorted_queue = sorted(self._queue, key=lambda j: -j.priority)
            job = sorted_queue[0]
            self._queue.remove(job)
            
            # Update job state
            job.status = JobStatus.IN_PROGRESS
            job.started_at = datetime.utcnow()
            job.updated_at = datetime.utcnow()
            
            # Track in progress
            self._in_progress[job.id] = job
            
            # Update metrics
            self._metrics.pending_jobs -= 1
            self._metrics.in_progress_jobs += 1
            
            return job
    
    async def complete(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark a job as completed."""
        async with self._lock:
            job = self._in_progress.pop(job_id, None)
            
            if job:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.updated_at = datetime.utcnow()
                
                self._completed.append(job)
                
                # Update metrics
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
        async with self._lock:
            job = self._in_progress.pop(job_id, None)
            
            if not job:
                logger.warning(f"Job not found for failure: {job_id}")
                return
            
            job.error_message = error
            job.updated_at = datetime.utcnow()
            
            if retry and job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.RETRYING
                
                # Re-enqueue with backoff (handled by caller)
                self._queue.append(job)
                self._metrics.pending_jobs += 1
                self._metrics.in_progress_jobs -= 1
                
                logger.info(f"Retrying job {job_id} (attempt {job.retry_count}/{job.max_retries})")
            else:
                job.status = JobStatus.DEAD_LETTER
                self._dead_letter.append(job)
                self._failed.append(job)
                
                # Update metrics
                self._metrics.in_progress_jobs -= 1
                self._metrics.failed_jobs += 1
                self._metrics.dead_letter_jobs += 1
                
                logger.error(f"Job {job_id} moved to dead letter queue: {error}")
    
    def _update_avg_processing_time(self) -> None:
        """Update average processing time metric."""
        if self._processing_times:
            # Keep last 1000 samples
            if len(self._processing_times) > 1000:
                self._processing_times = self._processing_times[-1000:]
            self._metrics.avg_processing_time_seconds = (
                sum(self._processing_times) / len(self._processing_times)
            )
    
    def get_metrics(self) -> QueueMetrics:
        """Get current queue metrics."""
        return self._metrics
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return len(self._queue)
    
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
    
    # Additional local-only methods for debugging
    
    def get_all_jobs(self) -> Dict[str, List[JobData]]:
        """Get all jobs grouped by status (local debugging only)."""
        return {
            "pending": list(self._queue),
            "in_progress": list(self._in_progress.values()),
            "completed": self._completed[-100:],  # Last 100
            "failed": self._failed[-100:],
            "dead_letter": self._dead_letter,
        }
    
    def clear_completed(self) -> int:
        """Clear completed jobs (local maintenance)."""
        count = len(self._completed)
        self._completed.clear()
        return count

