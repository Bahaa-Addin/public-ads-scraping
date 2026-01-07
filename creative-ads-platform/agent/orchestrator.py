"""
Orchestrator - Dependency Injection and Component Management

The orchestrator is responsible for:
1. Detecting the current mode (local/cloud)
2. Injecting the correct adapter implementations
3. Wiring up all components
4. Starting and stopping the system

This module ensures business logic NEVER imports cloud SDKs directly.
All dependencies are injected through interfaces.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Optional

from .config import Config, Mode
from .interfaces import (
    StorageInterface,
    QueueInterface,
    LLMInterface,
    MonitoringInterface,
)
from .agent_brain import AgentBrain

logger = logging.getLogger(__name__)


@dataclass
class AdapterRegistry:
    """Registry holding all adapter instances."""
    storage: StorageInterface
    queue: QueueInterface
    llm: LLMInterface
    monitoring: MonitoringInterface


class Orchestrator:
    """
    Central orchestrator for the Creative Ads Platform.
    
    Responsibilities:
    - Detect execution mode from environment
    - Create and inject appropriate adapters
    - Initialize all components
    - Provide unified access to services
    
    Usage:
        orchestrator = Orchestrator()
        await orchestrator.initialize()
        
        # Access adapters through registry
        await orchestrator.adapters.storage.store_asset(...)
        await orchestrator.adapters.queue.enqueue(...)
        
        # Or through convenience methods
        storage = orchestrator.get_storage()
        queue = orchestrator.get_queue()
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
        self._adapters: Optional[AdapterRegistry] = None
        self._agent: Optional[AgentBrain] = None
        self._initialized = False
        
    @property
    def adapters(self) -> AdapterRegistry:
        """Get the adapter registry."""
        if not self._adapters:
            raise RuntimeError("Orchestrator not initialized. Call initialize() first.")
        return self._adapters
    
    @property
    def mode(self) -> Mode:
        """Get the current execution mode."""
        if self.config:
            return self.config.mode
        mode_str = os.environ.get("MODE", "local").lower()
        return Mode.CLOUD if mode_str == "cloud" else Mode.LOCAL
    
    async def initialize(self) -> None:
        """
        Initialize the orchestrator and all adapters.
        
        This method:
        1. Loads configuration
        2. Creates appropriate adapters based on mode
        3. Initializes all adapters
        """
        logger.info(f"Initializing Orchestrator in {self.mode.value} mode...")
        
        # Load config if not provided
        if not self.config:
            self.config = Config.from_environment()
        
        # Validate config
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        # Create adapters based on mode
        self._adapters = await self._create_adapters()
        
        # Initialize all adapters
        await self._initialize_adapters()
        
        self._initialized = True
        logger.info(f"Orchestrator initialized in {self.mode.value} mode")
        
        # Log adapter summary
        self._log_adapter_summary()
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all adapters."""
        logger.info("Shutting down Orchestrator...")
        
        if self._adapters:
            # Close adapters in reverse order
            try:
                await self._adapters.monitoring.close()
            except Exception as e:
                logger.error(f"Error closing monitoring: {e}")
            
            try:
                await self._adapters.llm.close()
            except Exception as e:
                logger.error(f"Error closing LLM: {e}")
            
            try:
                await self._adapters.queue.close()
            except Exception as e:
                logger.error(f"Error closing queue: {e}")
            
            try:
                await self._adapters.storage.close()
            except Exception as e:
                logger.error(f"Error closing storage: {e}")
        
        self._initialized = False
        logger.info("Orchestrator shutdown complete")
    
    async def _create_adapters(self) -> AdapterRegistry:
        """Create adapter instances based on mode."""
        if self.mode == Mode.LOCAL:
            return await self._create_local_adapters()
        else:
            return await self._create_cloud_adapters()
    
    async def _create_local_adapters(self) -> AdapterRegistry:
        """Create local adapter instances."""
        logger.info("Creating local adapters...")
        
        # Import local adapters
        from .adapters.local import (
            LocalStorage,
            LocalQueue,
            LocalLLM,
            LocalMonitoring,
        )
        
        # Create storage adapter
        storage = LocalStorage(
            data_dir=self.config.data_dir,
            collection_prefix=self.config.firestore_collection_prefix,
        )
        
        # Create queue adapter
        queue = LocalQueue(
            max_queue_size=self.config.low_ram.max_queue_size,
        )
        
        # Create LLM adapter
        llm_mode = self.config.llm_mode
        if llm_mode == "vertex":
            # CRITICAL: Prevent Vertex in local mode
            raise RuntimeError(
                "Vertex AI is NOT available in local mode. "
                "Use LLM_MODE=template or LLM_MODE=ollama."
            )
        
        llm = LocalLLM(
            mode=llm_mode,
            ollama_host=self.config.ollama.host,
            ollama_model=self.config.ollama.model,
        )
        
        # Create monitoring adapter
        monitoring = LocalMonitoring(
            data_dir=self.config.data_dir,
        )
        
        return AdapterRegistry(
            storage=storage,
            queue=queue,
            llm=llm,
            monitoring=monitoring,
        )
    
    async def _create_cloud_adapters(self) -> AdapterRegistry:
        """Create cloud adapter instances."""
        logger.info("Creating cloud adapters...")
        
        # Import cloud adapters (only works in cloud mode)
        from .adapters.cloud import (
            FirestoreStorage,
            PubSubQueue,
            VertexLLM,
            CloudMonitoring,
        )
        
        # Create storage adapter
        storage = FirestoreStorage(
            project_id=self.config.gcp_project_id,
            collection_prefix=self.config.firestore_collection_prefix,
            database_id=self.config.firestore_database_id,
            storage_bucket_raw=self.config.storage_bucket_raw,
            storage_bucket_processed=self.config.storage_bucket_processed,
        )
        
        # Create queue adapter
        queue = PubSubQueue(
            project_id=self.config.gcp_project_id,
            topic_name=self.config.pubsub_topic,
            subscription_name=self.config.pubsub_subscription,
            dlq_topic_name=self.config.pubsub_dlq_topic,
        )
        
        # Create LLM adapter (Vertex AI in cloud mode)
        llm = VertexLLM(
            project_id=self.config.gcp_project_id,
            location=self.config.vertex_ai.location if self.config.vertex_ai else "us-central1",
            model_name=self.config.vertex_ai.model_name if self.config.vertex_ai else "gemini-1.5-pro",
        )
        
        # Create monitoring adapter
        monitoring = CloudMonitoring(
            project_id=self.config.gcp_project_id,
        )
        
        return AdapterRegistry(
            storage=storage,
            queue=queue,
            llm=llm,
            monitoring=monitoring,
        )
    
    async def _initialize_adapters(self) -> None:
        """Initialize all adapters."""
        logger.info("Initializing adapters...")
        
        # Initialize in order
        await self._adapters.storage.connect()
        await self._adapters.queue.initialize()
        await self._adapters.llm.initialize()
        await self._adapters.monitoring.initialize()
        
        logger.info("All adapters initialized")
    
    def _log_adapter_summary(self) -> None:
        """Log summary of active adapters."""
        adapters = self._adapters
        
        summary = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     CREATIVE ADS PLATFORM - ADAPTER SUMMARY                  ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Mode:       {self.mode.value.upper():10}                                               ║
║  Storage:    {type(adapters.storage).__name__:30}                          ║
║  Queue:      {type(adapters.queue).__name__:30}                          ║
║  LLM:        {type(adapters.llm).__name__:30}                          ║
║  Monitoring: {type(adapters.monitoring).__name__:30}                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        logger.info(summary)
    
    # Convenience accessor methods
    
    def get_storage(self) -> StorageInterface:
        """Get the storage adapter."""
        return self.adapters.storage
    
    def get_queue(self) -> QueueInterface:
        """Get the queue adapter."""
        return self.adapters.queue
    
    def get_llm(self) -> LLMInterface:
        """Get the LLM adapter."""
        return self.adapters.llm
    
    def get_monitoring(self) -> MonitoringInterface:
        """Get the monitoring adapter."""
        return self.adapters.monitoring
    
    def get_agent(self) -> AgentBrain:
        """Get or create the AgentBrain instance."""
        if self._agent is None:
            self._agent = AgentBrain(
                config=self.config,
                job_queue=self.adapters.queue,
                storage=self.adapters.storage,
                llm=self.adapters.llm,
                monitoring=self.adapters.monitoring,
            )
        return self._agent
    
    # Health check methods
    
    async def health_check(self) -> dict:
        """Run health checks on all adapters."""
        results = {
            "mode": self.mode.value,
            "healthy": True,
            "components": {},
        }
        
        # Check each adapter
        try:
            results["components"]["storage"] = await self._adapters.storage.health_check()
        except Exception as e:
            results["components"]["storage"] = False
            logger.error(f"Storage health check failed: {e}")
        
        try:
            results["components"]["queue"] = await self._adapters.queue.health_check()
        except Exception as e:
            results["components"]["queue"] = False
            logger.error(f"Queue health check failed: {e}")
        
        try:
            results["components"]["llm"] = await self._adapters.llm.health_check()
        except Exception as e:
            results["components"]["llm"] = False
            logger.error(f"LLM health check failed: {e}")
        
        # Overall health
        results["healthy"] = all(results["components"].values())
        
        return results


# Global orchestrator instance (singleton pattern)
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


async def initialize_orchestrator(config: Optional[Config] = None) -> Orchestrator:
    """Initialize the global orchestrator."""
    global _orchestrator
    _orchestrator = Orchestrator(config)
    await _orchestrator.initialize()
    return _orchestrator


async def shutdown_orchestrator() -> None:
    """Shutdown the global orchestrator."""
    global _orchestrator
    if _orchestrator:
        await _orchestrator.shutdown()
        _orchestrator = None

