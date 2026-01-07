"""
Cloud Monitoring Adapter

Implements MonitoringInterface using Google Cloud Monitoring.
CLOUD MODE ONLY.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from agent.interfaces.monitoring import (
    MonitoringInterface,
    MetricData,
    MetricType,
    LogLevel,
    HealthStatus,
)

logger = logging.getLogger(__name__)


class CloudMonitoring(MonitoringInterface):
    """
    Google Cloud Monitoring implementation.
    
    Uses:
    - Cloud Monitoring for metrics
    - Cloud Logging for logs
    
    CLOUD MODE ONLY - requires GCP credentials.
    """
    
    def __init__(
        self,
        project_id: str,
        location: str = "global",
    ):
        self._validate_mode()
        
        self.project_id = project_id
        self.location = location
        
        self._metrics_client = None
        self._logging_client = None
        self._health_status = HealthStatus(healthy=True)
        self._pipeline_metrics: Dict[str, Dict[str, Any]] = {}
        
    def _validate_mode(self) -> None:
        """Validate that we're in cloud mode."""
        mode = os.environ.get("MODE", "local").lower()
        if mode != "cloud":
            raise RuntimeError(
                "CloudMonitoring is only available in cloud mode. "
                "Set MODE=cloud to use cloud adapters, or use LocalMonitoring for local development."
            )
    
    async def initialize(self) -> None:
        """Initialize Cloud Monitoring clients."""
        from google.cloud import monitoring_v3
        from google.cloud import logging as cloud_logging
        
        self._metrics_client = monitoring_v3.MetricServiceClient()
        self._logging_client = cloud_logging.Client(project=self.project_id)
        
        logger.info(f"Initialized Cloud Monitoring for project: {self.project_id}")
    
    async def close(self) -> None:
        """Close Cloud Monitoring connections."""
        logger.info("Cloud Monitoring closed")
    
    # Metrics Operations
    
    async def record_metric(self, metric: MetricData) -> None:
        """Record a metric data point."""
        from google.cloud import monitoring_v3
        from google.protobuf import timestamp_pb2
        
        series = monitoring_v3.TimeSeries()
        series.metric.type = f"custom.googleapis.com/creative_ads/{metric.name}"
        series.resource.type = "global"
        series.resource.labels["project_id"] = self.project_id
        
        # Add labels
        for key, value in metric.labels.items():
            series.metric.labels[key] = value
        
        # Create data point
        point = monitoring_v3.Point()
        
        now = datetime.utcnow()
        point.interval.end_time.seconds = int(now.timestamp())
        
        if metric.metric_type == MetricType.COUNTER:
            point.value.int64_value = int(metric.value)
        else:
            point.value.double_value = metric.value
        
        series.points.append(point)
        
        # Write to Cloud Monitoring
        project_path = f"projects/{self.project_id}"
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._metrics_client.create_time_series(
                name=project_path,
                time_series=[series]
            )
        )
    
    async def increment_counter(
        self,
        name: str,
        value: int = 1,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        metric = MetricData(
            name=name,
            value=float(value),
            metric_type=MetricType.COUNTER,
            labels=labels or {}
        )
        await self.record_metric(metric)
    
    async def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric value."""
        metric = MetricData(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels or {}
        )
        await self.record_metric(metric)
    
    async def record_histogram(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a histogram metric value."""
        metric = MetricData(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            labels=labels or {}
        )
        await self.record_metric(metric)
    
    async def get_metrics(
        self,
        name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[MetricData]:
        """Get recorded metrics from Cloud Monitoring."""
        from google.cloud import monitoring_v3
        
        project_path = f"projects/{self.project_id}"
        
        # Build filter
        filter_str = 'metric.type = starts_with("custom.googleapis.com/creative_ads/")'
        if name:
            filter_str = f'metric.type = "custom.googleapis.com/creative_ads/{name}"'
        
        # Build time interval
        interval = monitoring_v3.TimeInterval()
        interval.end_time.seconds = int((end_time or datetime.utcnow()).timestamp())
        if start_time:
            interval.start_time.seconds = int(start_time.timestamp())
        
        # Query metrics
        results = self._metrics_client.list_time_series(
            request={
                "name": project_path,
                "filter": filter_str,
                "interval": interval,
            }
        )
        
        metrics = []
        for series in results:
            metric_name = series.metric.type.replace("custom.googleapis.com/creative_ads/", "")
            for point in series.points:
                metrics.append(MetricData(
                    name=metric_name,
                    value=point.value.double_value or point.value.int64_value,
                    metric_type=MetricType.GAUGE,
                    timestamp=datetime.fromtimestamp(point.interval.end_time.seconds),
                    labels=dict(series.metric.labels)
                ))
        
        return metrics
    
    # Logging Operations
    
    async def log(
        self,
        level: LogLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a message to Cloud Logging."""
        cloud_logger = self._logging_client.logger("creative-ads-platform")
        
        severity_map = {
            LogLevel.DEBUG: "DEBUG",
            LogLevel.INFO: "INFO",
            LogLevel.WARNING: "WARNING",
            LogLevel.ERROR: "ERROR",
            LogLevel.CRITICAL: "CRITICAL",
        }
        
        struct = {
            "message": message,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        cloud_logger.log_struct(struct, severity=severity_map.get(level, "INFO"))
    
    async def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an error to Cloud Logging."""
        import traceback
        
        cloud_logger = self._logging_client.logger("creative-ads-platform")
        
        struct = {
            "message": str(error),
            "error_type": type(error).__name__,
            "stack_trace": traceback.format_exc(),
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        cloud_logger.log_struct(struct, severity="ERROR")
    
    async def get_logs(
        self,
        level: Optional[LogLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get log entries from Cloud Logging."""
        # Build filter
        filter_parts = [f'logName="projects/{self.project_id}/logs/creative-ads-platform"']
        
        if level:
            severity_map = {
                LogLevel.DEBUG: "DEBUG",
                LogLevel.INFO: "INFO",
                LogLevel.WARNING: "WARNING",
                LogLevel.ERROR: "ERROR",
                LogLevel.CRITICAL: "CRITICAL",
            }
            filter_parts.append(f'severity="{severity_map.get(level, "INFO")}"')
        
        if start_time:
            filter_parts.append(f'timestamp>="{start_time.isoformat()}Z"')
        
        if end_time:
            filter_parts.append(f'timestamp<="{end_time.isoformat()}Z"')
        
        filter_str = " AND ".join(filter_parts)
        
        entries = self._logging_client.list_entries(
            filter_=filter_str,
            max_results=limit,
            order_by="timestamp desc"
        )
        
        return [
            {
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "severity": entry.severity,
                "payload": entry.payload,
            }
            for entry in entries
        ]
    
    # Health Monitoring
    
    async def report_health(self, status: HealthStatus) -> None:
        """Report system health status."""
        self._health_status = status
        
        # Log health status
        await self.log(
            LogLevel.INFO,
            f"Health status: {'healthy' if status.healthy else 'unhealthy'}",
            context=status.to_dict()
        )
        
        # Record metrics
        await self.set_gauge(
            "system_health",
            1.0 if status.healthy else 0.0
        )
        
        for component, is_healthy in status.components.items():
            await self.set_gauge(
                f"component_health_{component}",
                1.0 if is_healthy else 0.0
            )
    
    async def get_health(self) -> HealthStatus:
        """Get current system health status."""
        return self._health_status
    
    # Pipeline Metrics
    
    async def record_pipeline_event(
        self,
        stage: str,
        event_type: str,
        duration_seconds: Optional[float] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a pipeline event."""
        # Update local aggregation
        if stage not in self._pipeline_metrics:
            self._pipeline_metrics[stage] = {
                "total": 0,
                "success": 0,
                "failure": 0,
                "total_duration": 0.0,
            }
        
        metrics = self._pipeline_metrics[stage]
        metrics["total"] += 1
        
        if success:
            metrics["success"] += 1
        else:
            metrics["failure"] += 1
        
        if duration_seconds:
            metrics["total_duration"] += duration_seconds
        
        # Record to Cloud Monitoring
        await self.increment_counter(
            f"pipeline_{stage}_{event_type}",
            labels={"success": str(success)}
        )
        
        if duration_seconds:
            await self.record_histogram(
                f"pipeline_{stage}_duration",
                duration_seconds
            )
    
    async def get_pipeline_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get pipeline metrics summary."""
        summary = {}
        
        for stage, metrics in self._pipeline_metrics.items():
            avg_duration = 0.0
            if metrics["total"] > 0:
                avg_duration = metrics["total_duration"] / metrics["total"]
            
            summary[stage] = {
                "total": metrics["total"],
                "success": metrics["success"],
                "failure": metrics["failure"],
                "success_rate": metrics["success"] / max(metrics["total"], 1),
                "avg_duration_seconds": avg_duration,
            }
        
        return summary

