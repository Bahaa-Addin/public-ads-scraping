"""
Monitoring Interface

Defines the contract for monitoring and metrics operations.
Implementations: LocalMonitoring (logs + files), CloudMonitoring (GCP)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class LogLevel(Enum):
    """Log severity levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricData:
    """Represents a metric data point."""
    name: str
    value: float
    metric_type: MetricType = MetricType.COUNTER
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "metric_type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
        }


@dataclass
class HealthStatus:
    """System health status."""
    healthy: bool
    components: Dict[str, bool] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "healthy": self.healthy,
            "components": self.components,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class MonitoringInterface(ABC):
    """
    Abstract interface for monitoring operations.
    
    Implementations:
    - LocalMonitoring: Local logs and metrics files
    - CloudMonitoring: Google Cloud Monitoring
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize monitoring client."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close monitoring connections."""
        pass
    
    # Metrics Operations
    
    @abstractmethod
    async def record_metric(self, metric: MetricData) -> None:
        """Record a metric data point."""
        pass
    
    @abstractmethod
    async def increment_counter(
        self,
        name: str,
        value: int = 1,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        pass
    
    @abstractmethod
    async def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric value."""
        pass
    
    @abstractmethod
    async def record_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a histogram metric value."""
        pass
    
    @abstractmethod
    async def get_metrics(
        self,
        name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[MetricData]:
        """Get recorded metrics."""
        pass
    
    # Logging Operations
    
    @abstractmethod
    async def log(
        self,
        level: LogLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a message with context."""
        pass
    
    @abstractmethod
    async def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an error with context and stack trace."""
        pass
    
    @abstractmethod
    async def get_logs(
        self,
        level: Optional[LogLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get log entries."""
        pass
    
    # Health Monitoring
    
    @abstractmethod
    async def report_health(self, status: HealthStatus) -> None:
        """Report system health status."""
        pass
    
    @abstractmethod
    async def get_health(self) -> HealthStatus:
        """Get current system health status."""
        pass
    
    # Pipeline Metrics
    
    @abstractmethod
    async def record_pipeline_event(
        self,
        stage: str,
        event_type: str,
        duration_seconds: Optional[float] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a pipeline event (scrape, extract, generate, etc.)."""
        pass
    
    @abstractmethod
    async def get_pipeline_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get pipeline metrics summary."""
        pass

