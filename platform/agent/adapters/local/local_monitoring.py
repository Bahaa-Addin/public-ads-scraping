"""
Local Monitoring Adapter

Implements MonitoringInterface using local files and logs.
Emulates Google Cloud Monitoring for local development.

Data is stored in:
- /data/logs/*.json - Log entries
- /data/metrics/*.json - Metric data
"""

import asyncio
import json
import logging
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.interfaces.monitoring import (
    MonitoringInterface,
    MetricData,
    MetricType,
    LogLevel,
    HealthStatus,
)

logger = logging.getLogger(__name__)


class LocalMonitoring(MonitoringInterface):
    """
    Local monitoring implementation using files and logs.
    
    Provides:
    - File-based metric storage
    - Local log aggregation
    - Health status tracking
    - Pipeline event recording
    """
    
    def __init__(
        self,
        data_dir: str = "./data",
        max_log_entries: int = 10000,
        max_metric_entries: int = 100000
    ):
        self.data_dir = Path(data_dir)
        self.logs_dir = self.data_dir / "logs"
        self.metrics_dir = self.data_dir / "metrics"
        
        self.max_log_entries = max_log_entries
        self.max_metric_entries = max_metric_entries
        
        # In-memory buffers for batch writes
        self._log_buffer: List[Dict[str, Any]] = []
        self._metric_buffer: List[MetricData] = []
        self._buffer_size = 100
        
        # Health status
        self._health_status = HealthStatus(
            healthy=True,
            components={},
            details={}
        )
        
        # Pipeline metrics aggregation
        self._pipeline_metrics: Dict[str, Dict[str, Any]] = {}
        
    async def initialize(self) -> None:
        """Initialize monitoring directories."""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized local monitoring at {self.data_dir}")
    
    async def close(self) -> None:
        """Flush buffers and close monitoring."""
        await self._flush_logs()
        await self._flush_metrics()
        logger.info("Local monitoring closed")
    
    # Internal methods
    
    async def _flush_logs(self) -> None:
        """Flush log buffer to disk."""
        if not self._log_buffer:
            return
        
        date_str = datetime.utcnow().strftime("%Y%m%d")
        log_file = self.logs_dir / f"logs_{date_str}.json"
        
        # Load existing logs
        existing = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        
        # Append new logs
        existing.extend(self._log_buffer)
        
        # Trim if too large
        if len(existing) > self.max_log_entries:
            existing = existing[-self.max_log_entries:]
        
        # Write back
        with open(log_file, 'w') as f:
            json.dump(existing, f, indent=2, default=str)
        
        self._log_buffer.clear()
    
    async def _flush_metrics(self) -> None:
        """Flush metric buffer to disk."""
        if not self._metric_buffer:
            return
        
        date_str = datetime.utcnow().strftime("%Y%m%d")
        metrics_file = self.metrics_dir / f"metrics_{date_str}.json"
        
        # Load existing metrics
        existing = []
        if metrics_file.exists():
            try:
                with open(metrics_file, 'r') as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        
        # Append new metrics
        for metric in self._metric_buffer:
            existing.append(metric.to_dict())
        
        # Trim if too large
        if len(existing) > self.max_metric_entries:
            existing = existing[-self.max_metric_entries:]
        
        # Write back
        with open(metrics_file, 'w') as f:
            json.dump(existing, f, indent=2, default=str)
        
        self._metric_buffer.clear()
    
    # Metrics Operations
    
    async def record_metric(self, metric: MetricData) -> None:
        """Record a metric data point."""
        self._metric_buffer.append(metric)
        
        if len(self._metric_buffer) >= self._buffer_size:
            await self._flush_metrics()
    
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
        """Get recorded metrics."""
        await self._flush_metrics()
        
        result = []
        
        for metrics_file in sorted(self.metrics_dir.glob("metrics_*.json")):
            try:
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                
                for entry in data:
                    # Filter by name
                    if name and entry.get("name") != name:
                        continue
                    
                    # Filter by time
                    timestamp = datetime.fromisoformat(entry.get("timestamp", ""))
                    if start_time and timestamp < start_time:
                        continue
                    if end_time and timestamp > end_time:
                        continue
                    
                    result.append(MetricData(
                        name=entry["name"],
                        value=entry["value"],
                        metric_type=MetricType(entry.get("metric_type", "counter")),
                        timestamp=timestamp,
                        labels=entry.get("labels", {})
                    ))
                    
            except Exception as e:
                logger.error(f"Error reading metrics file {metrics_file}: {e}")
        
        return result
    
    # Logging Operations
    
    async def log(
        self,
        level: LogLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a message with context."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "message": message,
            "context": context or {}
        }
        
        self._log_buffer.append(entry)
        
        # Also log to standard logger
        log_method = getattr(logger, level.value, logger.info)
        log_method(f"{message} {context}" if context else message)
        
        if len(self._log_buffer) >= self._buffer_size:
            await self._flush_logs()
    
    async def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an error with context and stack trace."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": LogLevel.ERROR.value,
            "message": str(error),
            "error_type": type(error).__name__,
            "stack_trace": traceback.format_exc(),
            "context": context or {}
        }
        
        self._log_buffer.append(entry)
        logger.error(f"{type(error).__name__}: {error}", exc_info=True)
        
        if len(self._log_buffer) >= self._buffer_size:
            await self._flush_logs()
    
    async def get_logs(
        self,
        level: Optional[LogLevel] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get log entries."""
        await self._flush_logs()
        
        result = []
        
        for log_file in sorted(self.logs_dir.glob("logs_*.json"), reverse=True):
            if len(result) >= limit:
                break
                
            try:
                with open(log_file, 'r') as f:
                    data = json.load(f)
                
                for entry in reversed(data):
                    if len(result) >= limit:
                        break
                    
                    # Filter by level
                    if level and entry.get("level") != level.value:
                        continue
                    
                    # Filter by time
                    timestamp = datetime.fromisoformat(entry.get("timestamp", ""))
                    if start_time and timestamp < start_time:
                        continue
                    if end_time and timestamp > end_time:
                        continue
                    
                    result.append(entry)
                    
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
        
        return result
    
    # Health Monitoring
    
    async def report_health(self, status: HealthStatus) -> None:
        """Report system health status."""
        self._health_status = status
        
        # Write to health file
        health_file = self.data_dir / "health.json"
        with open(health_file, 'w') as f:
            json.dump(status.to_dict(), f, indent=2)
    
    async def get_health(self) -> HealthStatus:
        """Get current system health status."""
        # Try to read from file
        health_file = self.data_dir / "health.json"
        if health_file.exists():
            try:
                with open(health_file, 'r') as f:
                    data = json.load(f)
                return HealthStatus(
                    healthy=data.get("healthy", True),
                    components=data.get("components", {}),
                    details=data.get("details", {}),
                    timestamp=datetime.fromisoformat(data.get("timestamp", datetime.utcnow().isoformat()))
                )
            except Exception:
                pass
        
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
        # Update aggregated metrics
        if stage not in self._pipeline_metrics:
            self._pipeline_metrics[stage] = {
                "total": 0,
                "success": 0,
                "failure": 0,
                "total_duration": 0.0,
                "events": []
            }
        
        metrics = self._pipeline_metrics[stage]
        metrics["total"] += 1
        
        if success:
            metrics["success"] += 1
        else:
            metrics["failure"] += 1
        
        if duration_seconds:
            metrics["total_duration"] += duration_seconds
        
        # Record event
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": stage,
            "event_type": event_type,
            "duration_seconds": duration_seconds,
            "success": success,
            "metadata": metadata or {}
        }
        
        metrics["events"].append(event)
        
        # Keep last 1000 events per stage
        if len(metrics["events"]) > 1000:
            metrics["events"] = metrics["events"][-1000:]
        
        # Also record as metric
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

