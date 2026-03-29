"""
Interface definitions for the Agentic Ads Platform.

These interfaces define the contracts that adapters must implement.
Business logic ONLY imports these interfaces - never cloud SDKs directly.
"""

from .storage import StorageInterface, AssetData
from .queue import QueueInterface, JobData, JobStatus
from .llm import LLMInterface, PromptResult
from .monitoring import MonitoringInterface, MetricData

__all__ = [
    "StorageInterface",
    "AssetData",
    "QueueInterface", 
    "JobData",
    "JobStatus",
    "LLMInterface",
    "PromptResult",
    "MonitoringInterface",
    "MetricData",
]

