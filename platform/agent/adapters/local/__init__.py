"""
Local Adapters for Development

These adapters provide local implementations that don't require cloud services.
All cloud services are emulated locally:

- LocalStorage: JSON files + filesystem (emulates Firestore + GCS)
- LocalQueue: In-memory queue (emulates Pub/Sub)
- LocalLLM: Template-based + optional Ollama (NO Vertex AI)
- LocalMonitoring: Local logs + metrics files

IMPORTANT: Vertex AI is NOT available in local mode.
Use templates or Ollama for reverse-prompt generation locally.
"""

from .local_storage import LocalStorage
from .local_queue import LocalQueue
from .local_llm import LocalLLM
from .local_monitoring import LocalMonitoring

__all__ = [
    "LocalStorage",
    "LocalQueue",
    "LocalLLM",
    "LocalMonitoring",
]

