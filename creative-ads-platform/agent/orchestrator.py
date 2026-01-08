"""
Orchestrator - Dependency Injection and Component Management

The orchestrator is responsible for:
1. Detecting the current mode (local/cloud)
2. Injecting the correct adapter implementations
3. Wiring up all components
4. Starting and stopping the system
5. Emitting SSE events to the dashboard for real-time monitoring

This module ensures business logic NEVER imports cloud SDKs directly.
All dependencies are injected through interfaces.
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

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
        self._dashboard_url: Optional[str] = None
        self._http_client: Optional[httpx.AsyncClient] = None
        self._stream_manager: Optional[Any] = None  # StreamManager instance
    
    def set_stream_manager(self, stream_manager: Any) -> None:
        """
        Set the StreamManager instance for live browser streaming.
        
        Args:
            stream_manager: StreamManager instance from services
        """
        self._stream_manager = stream_manager
        logger.info("StreamManager attached to Orchestrator")
    
    def get_stream_manager(self) -> Optional[Any]:
        """Get the StreamManager instance."""
        return self._stream_manager
        
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
        
        # Initialize dashboard event emitter
        self._dashboard_url = os.environ.get("DASHBOARD_API_URL", "http://localhost:8000")
        self._http_client = httpx.AsyncClient(timeout=5.0)
    
    # ==========================================================================
    # SSE Event Emission Methods
    # ==========================================================================
    
    async def emit_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        job_id: Optional[str] = None
    ) -> None:
        """
        Emit an event to the dashboard SSE stream.
        
        Event types:
        - pipeline_started: Full pipeline began
        - step_started: Individual step began (scrape, extract, generate, classify)
        - step_progress: Progress update with percentage
        - asset_scraped: New asset scraped (includes preview)
        - screenshot_captured: Screenshot taken (includes URL)
        - features_extracted: Features computed for asset
        - prompt_generated: Prompt created for asset
        - step_completed: Step finished with results
        - pipeline_completed: Full pipeline finished
        - error: Error occurred
        """
        if not self._http_client or not self._dashboard_url:
            logger.warning("Dashboard event emitter not initialized")
            return
        
        try:
            await self._http_client.post(
                f"{self._dashboard_url}/api/v1/events/emit",
                params={
                    "event_type": event_type,
                    "job_id": job_id,
                },
                json=data,
            )
            logger.debug(f"Emitted event: {event_type}")
        except Exception as e:
            logger.warning(f"Failed to emit event to dashboard: {e}")
    
    async def emit_pipeline_started(
        self,
        job_id: str,
        sources: list,
        query: Optional[str] = None,
        steps: Optional[list] = None
    ) -> None:
        """Emit pipeline started event."""
        await self.emit_event(
            "pipeline_started",
            {
                "message": f"Pipeline started for {len(sources)} source(s)",
                "sources": sources,
                "query": query,
                "steps": steps or ["scrape", "extract", "generate", "classify"],
            },
            job_id=job_id,
        )
    
    async def emit_step_started(
        self,
        job_id: str,
        step_name: str,
        message: Optional[str] = None
    ) -> None:
        """Emit step started event."""
        await self.emit_event(
            "step_started",
            {
                "step": step_name,
                "message": message or f"Starting {step_name}...",
            },
            job_id=job_id,
        )
    
    async def emit_step_progress(
        self,
        job_id: str,
        step_name: str,
        progress: float,
        message: Optional[str] = None
    ) -> None:
        """Emit step progress event."""
        await self.emit_event(
            "step_progress",
            {
                "step": step_name,
                "progress": progress,
                "message": message or f"{step_name}: {progress:.0f}%",
            },
            job_id=job_id,
        )
    
    async def emit_asset_scraped(
        self,
        job_id: str,
        asset_id: str,
        title: Optional[str] = None,
        source: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> None:
        """Emit asset scraped event."""
        await self.emit_event(
            "asset_scraped",
            {
                "asset_id": asset_id,
                "title": title,
                "source": source,
                "image_url": image_url,
                "message": f"Scraped: {title or asset_id}",
            },
            job_id=job_id,
        )
    
    async def emit_screenshot_captured(
        self,
        job_id: str,
        asset_id: str,
        screenshot_url: str
    ) -> None:
        """Emit screenshot captured event."""
        await self.emit_event(
            "screenshot_captured",
            {
                "asset_id": asset_id,
                "screenshot_url": screenshot_url,
                "message": "Screenshot captured",
            },
            job_id=job_id,
        )
    
    async def emit_features_extracted(
        self,
        job_id: str,
        asset_id: str,
        features: Dict[str, Any]
    ) -> None:
        """Emit features extracted event."""
        await self.emit_event(
            "features_extracted",
            {
                "asset_id": asset_id,
                "features": features,
                "message": f"Features extracted for {asset_id}",
            },
            job_id=job_id,
        )
    
    async def emit_prompt_generated(
        self,
        job_id: str,
        asset_id: str,
        prompt: str
    ) -> None:
        """Emit prompt generated event."""
        await self.emit_event(
            "prompt_generated",
            {
                "asset_id": asset_id,
                "prompt": prompt[:200] + "..." if len(prompt) > 200 else prompt,
                "message": f"Prompt generated for {asset_id}",
            },
            job_id=job_id,
        )
    
    async def emit_step_completed(
        self,
        job_id: str,
        step_name: str,
        results: Dict[str, Any]
    ) -> None:
        """Emit step completed event."""
        await self.emit_event(
            "step_completed",
            {
                "step": step_name,
                "results": results,
                "message": f"{step_name} completed",
            },
            job_id=job_id,
        )
    
    async def emit_pipeline_completed(
        self,
        job_id: str,
        duration_seconds: float,
        assets_count: int,
        prompts_count: int
    ) -> None:
        """Emit pipeline completed event."""
        await self.emit_event(
            "pipeline_completed",
            {
                "duration_seconds": duration_seconds,
                "assets_count": assets_count,
                "prompts_count": prompts_count,
                "message": f"Pipeline completed in {duration_seconds:.1f}s",
            },
            job_id=job_id,
        )
    
    async def emit_error(
        self,
        job_id: str,
        step_name: str,
        error_message: str
    ) -> None:
        """Emit error event."""
        await self.emit_event(
            "error",
            {
                "step": step_name,
                "error": error_message,
                "message": f"Error in {step_name}: {error_message}",
            },
            job_id=job_id,
        )
    
    # ==========================================================================
    # Live Streaming Integration
    # ==========================================================================
    
    async def start_screencast(
        self,
        session_id: str,
        job_id: str,
        page: Any,
        source: str = "unknown"
    ) -> bool:
        """
        Start live screencast for a Playwright page.
        
        Call this when a scraper begins working with a page to enable
        real-time streaming to the dashboard.
        
        Args:
            session_id: Unique session identifier
            job_id: Associated job ID
            page: Playwright Page object
            source: Scraper source name
            
        Returns:
            True if screencast started successfully
        """
        if not self._stream_manager:
            logger.debug("StreamManager not available, skipping screencast")
            return False
        
        try:
            result = await self._stream_manager.start_screencast(
                session_id=session_id,
                job_id=job_id,
                page=page,
                source=source,
            )
            
            if result:
                # Emit event that stream started
                await self.emit_event(
                    "stream_started",
                    {
                        "session_id": session_id,
                        "source": source,
                        "message": f"Live stream started for {source}",
                    },
                    job_id=job_id,
                )
            
            return result
        except Exception as e:
            logger.error(f"Failed to start screencast: {e}")
            return False
    
    async def stop_screencast(self, session_id: str) -> bool:
        """
        Stop live screencast for a session.
        
        Call this when a scraper finishes working with a page.
        
        Args:
            session_id: The session to stop
            
        Returns:
            True if stopped successfully
        """
        if not self._stream_manager:
            return False
        
        try:
            return await self._stream_manager.stop_screencast(session_id)
        except Exception as e:
            logger.error(f"Failed to stop screencast: {e}")
            return False
    
    def update_stream_context(
        self,
        session_id: str,
        url: Optional[str] = None,
        action: Optional[str] = None
    ) -> None:
        """
        Update the context for a streaming session.
        
        Call this as the scraper navigates to provide context
        for screenshots and timeline display.
        
        Args:
            session_id: The session to update
            url: Current page URL
            action: Current action (e.g., "Clicking login", "Scrolling")
        """
        if self._stream_manager:
            self._stream_manager.update_session_context(session_id, url, action)
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all adapters."""
        logger.info("Shutting down Orchestrator...")
        
        # Close HTTP client
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        
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

