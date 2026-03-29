"""
Cloud Adapters for Production

These adapters provide Google Cloud Platform implementations.
They require GCP credentials and are used in cloud mode only.

- FirestoreStorage: Google Cloud Firestore
- PubSubQueue: Google Cloud Pub/Sub  
- VertexLLM: Vertex AI (CLOUD MODE ONLY!)
- CloudMonitoring: Google Cloud Monitoring

CRITICAL: VertexLLM is ONLY available in cloud mode.
Attempting to use it in local mode will raise VertexAINotAvailableError.
"""

import os

# Only import cloud adapters if in cloud mode or explicitly requested
# This prevents requiring cloud SDKs for local development

_MODE = os.environ.get("MODE", "local").lower()

if _MODE == "cloud":
    from .firestore_storage import FirestoreStorage
    from .pubsub_queue import PubSubQueue
    from .vertex_llm import VertexLLM
    from .cloud_monitoring import CloudMonitoring
    
    __all__ = [
        "FirestoreStorage",
        "PubSubQueue",
        "VertexLLM",
        "CloudMonitoring",
    ]
else:
    # Provide stub exports that will raise errors if used
    __all__ = []
    
    def _cloud_not_available(name: str):
        def _raise(*args, **kwargs):
            raise RuntimeError(
                f"{name} is only available in cloud mode. "
                f"Set MODE=cloud to use cloud adapters."
            )
        return _raise
    
    FirestoreStorage = _cloud_not_available("FirestoreStorage")
    PubSubQueue = _cloud_not_available("PubSubQueue")
    VertexLLM = _cloud_not_available("VertexLLM")
    CloudMonitoring = _cloud_not_available("CloudMonitoring")

