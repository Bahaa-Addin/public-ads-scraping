"""
Adapters for the Agentic Ads Platform.

This module provides adapter implementations for local and cloud modes.
Adapters are injected at runtime based on the MODE environment variable.

LOCAL MODE (MODE=local):
- LocalStorage: JSON files + filesystem
- LocalQueue: In-memory queue
- LocalLLM: Template-based + optional Ollama
- LocalMonitoring: Local logs + files

CLOUD MODE (MODE=cloud):
- FirestoreStorage: Google Cloud Firestore
- PubSubQueue: Google Cloud Pub/Sub
- VertexLLM: Vertex AI (CLOUD ONLY!)
- CloudMonitoring: Google Cloud Monitoring
"""

from .local import (
    LocalStorage,
    LocalQueue,
    LocalLLM,
    LocalMonitoring,
)

# Cloud adapters are imported conditionally to avoid requiring cloud SDKs locally
# See adapters/cloud/__init__.py for cloud adapter imports

__all__ = [
    # Local adapters (always available)
    "LocalStorage",
    "LocalQueue",
    "LocalLLM",
    "LocalMonitoring",
]

