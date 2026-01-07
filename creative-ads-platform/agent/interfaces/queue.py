"""
Queue Interface

Defines the contract for all job queue operations.
Implementations: LocalQueue (in-memory), PubSubQueue (cloud)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


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
class JobData:
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
    def from_dict(cls, data: Dict[str, Any]) -> "JobData":
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
class QueueMetrics:
    """Metrics for job queue monitoring."""
    total_jobs: int = 0
    pending_jobs: int = 0
    in_progress_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    dead_letter_jobs: int = 0
    avg_processing_time_seconds: float = 0.0
    jobs_per_minute: float = 0.0


class QueueInterface(ABC):
    """
    Abstract interface for job queue operations.
    
    Implementations:
    - LocalQueue: In-memory queue for local development
    - PubSubQueue: Google Cloud Pub/Sub for production
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the queue connection."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close queue connections."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if queue is healthy and accessible."""
        pass
    
    @abstractmethod
    def register_handler(self, job_type: JobType, handler: Callable) -> None:
        """Register a handler for a specific job type."""
        pass
    
    @abstractmethod
    async def enqueue(self, job: JobData) -> str:
        """Add a job to the queue. Returns job ID."""
        pass
    
    @abstractmethod
    async def enqueue_batch(self, jobs: List[JobData]) -> List[str]:
        """Add multiple jobs to the queue. Returns list of job IDs."""
        pass
    
    @abstractmethod
    async def dequeue(self, timeout_seconds: float = 10.0) -> Optional[JobData]:
        """Get the next job from the queue."""
        pass
    
    @abstractmethod
    async def complete(self, job_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Mark a job as completed."""
        pass
    
    @abstractmethod
    async def fail(self, job_id: str, error: str, retry: bool = True) -> None:
        """Mark a job as failed, optionally retrying."""
        pass
    
    @abstractmethod
    def get_metrics(self) -> QueueMetrics:
        """Get current queue metrics."""
        pass
    
    @abstractmethod
    def get_queue_size(self) -> int:
        """Get current queue size."""
        pass
    
    # Convenience methods for creating specific job types
    
    @abstractmethod
    async def create_scrape_job(
        self,
        source: str,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        priority: int = 0
    ) -> str:
        """Create and enqueue a scraping job."""
        pass
    
    @abstractmethod
    async def create_feature_extraction_job(
        self,
        asset_id: str,
        asset_url: str,
        asset_type: str = "image"
    ) -> str:
        """Create and enqueue a feature extraction job."""
        pass
    
    @abstractmethod
    async def create_prompt_generation_job(
        self,
        asset_id: str,
        features: Dict[str, Any],
        industry: Optional[str] = None
    ) -> str:
        """Create and enqueue a reverse-prompt generation job."""
        pass

