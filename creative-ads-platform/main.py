#!/usr/bin/env python3
"""
Creative Ads Platform - Main Entry Point

This is the main entry point for the local-first, cloud-optional
creative ads scraping and reverse-prompting platform.

Usage:
    # Local mode (default)
    python main.py
    
    # Cloud mode
    MODE=cloud GCP_PROJECT_ID=your-project python main.py

The platform will:
1. Detect execution mode (local/cloud)
2. Initialize appropriate adapters
3. Start the Agent Brain processing loop
4. Expose the REST API and dashboard
"""

import asyncio
import logging
import signal
import sys
import os
from typing import Optional

# Ensure proper imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.config import Config, Mode
from agent.orchestrator import Orchestrator, initialize_orchestrator, shutdown_orchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('platform.log')
    ]
)
logger = logging.getLogger(__name__)


class CreativeAdsPlatform:
    """
    Main platform orchestrator for the creative ads pipeline.
    
    This class:
    1. Detects the execution mode (local/cloud)
    2. Initializes the orchestrator with appropriate adapters
    3. Starts the Agent Brain
    4. Handles graceful shutdown
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config
        self.orchestrator: Optional[Orchestrator] = None
        self._shutdown_event = asyncio.Event()
        
    async def initialize(self) -> None:
        """Initialize all platform components."""
        logger.info("=" * 60)
        logger.info("CREATIVE ADS PLATFORM")
        logger.info("=" * 60)
        
        # Load config from environment if not provided
        if not self.config:
            self.config = Config.from_environment()
        
        # Log mode
        mode_str = "LOCAL" if self.config.is_local else "CLOUD"
        logger.info(f"Execution Mode: {mode_str}")
        
        if self.config.is_local:
            logger.info("✓ Running in LOCAL mode - no cloud dependencies")
            logger.info(f"✓ Data directory: {self.config.data_dir}")
            logger.info(f"✓ LLM mode: {self.config.llm_mode}")
        else:
            logger.info("✓ Running in CLOUD mode")
            logger.info(f"✓ GCP Project: {self.config.gcp_project_id}")
            logger.info("✓ Vertex AI: ENABLED")
        
        logger.info("-" * 60)
        
        # Initialize orchestrator (creates and wires adapters)
        self.orchestrator = await initialize_orchestrator(self.config)
        
        # Run health check
        health = await self.orchestrator.health_check()
        if health["healthy"]:
            logger.info("✓ All components healthy")
        else:
            logger.warning(f"⚠ Some components unhealthy: {health['components']}")
        
        logger.info("=" * 60)
        logger.info("Platform initialized successfully")
        logger.info("=" * 60)
        
    async def run(self) -> None:
        """Run the main platform loop."""
        try:
            await self.initialize()
            
            # Import and start Agent Brain
            from agent.agent_brain import AgentBrain
            from agent.interfaces.queue import JobType
            
            # Create Agent Brain with injected adapters
            brain = AgentBrain(
                config=self.config,
                job_queue=self.orchestrator.get_queue(),
                storage=self.orchestrator.get_storage(),
                llm=self.orchestrator.get_llm(),
                monitoring=self.orchestrator.get_monitoring(),
            )
            
            # Start processing
            await brain.start()
            
            logger.info("Platform running. Press Ctrl+C to stop.")
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
            # Stop Agent Brain
            await brain.stop()
            
        except Exception as e:
            logger.error(f"Platform error: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()
            
    async def shutdown(self) -> None:
        """Gracefully shutdown all platform components."""
        logger.info("Shutting down Creative Ads Platform...")
        
        await shutdown_orchestrator()
        
        logger.info("Platform shutdown complete")
        
    def request_shutdown(self) -> None:
        """Request a graceful shutdown."""
        self._shutdown_event.set()


def setup_signal_handlers(platform: CreativeAdsPlatform) -> None:
    """Setup signal handlers for graceful shutdown."""
    def handle_signal(sig, frame):
        logger.info(f"Received signal {sig}, initiating shutdown...")
        platform.request_shutdown()
        
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


async def main():
    """Main entry point."""
    # Print banner
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██████╗██████╗ ███████╗ █████╗ ████████╗██╗██╗   ██╗███████╗               ║
║  ██╔════╝██╔══██╗██╔════╝██╔══██╗╚══██╔══╝██║██║   ██║██╔════╝               ║
║  ██║     ██████╔╝█████╗  ███████║   ██║   ██║██║   ██║█████╗                 ║
║  ██║     ██╔══██╗██╔══╝  ██╔══██║   ██║   ██║╚██╗ ██╔╝██╔══╝                 ║
║  ╚██████╗██║  ██║███████╗██║  ██║   ██║   ██║ ╚████╔╝ ███████╗               ║
║   ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═══╝  ╚══════╝               ║
║                                                                               ║
║   █████╗ ██████╗ ███████╗    ██████╗ ██╗      █████╗ ████████╗███████╗       ║
║  ██╔══██╗██╔══██╗██╔════╝    ██╔══██╗██║     ██╔══██╗╚══██╔══╝██╔════╝       ║
║  ███████║██║  ██║███████╗    ██████╔╝██║     ███████║   ██║   █████╗         ║
║  ██╔══██║██║  ██║╚════██║    ██╔═══╝ ██║     ██╔══██║   ██║   ██╔══╝         ║
║  ██║  ██║██████╔╝███████║    ██║     ███████╗██║  ██║   ██║   ██║            ║
║  ╚═╝  ╚═╝╚═════╝ ╚══════╝    ╚═╝     ╚══════╝╚═╝  ╚═╝   ╚═╝   ╚═╝            ║
║                                                                               ║
║  Local-First • Cloud-Optional • Fully Explainable                            ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Detect and display mode
    mode = os.environ.get("MODE", "local").lower()
    if mode == "local":
        print("🏠 Running in LOCAL MODE - No cloud dependencies\n")
    else:
        print("☁️  Running in CLOUD MODE - GCP services enabled\n")
    
    platform = CreativeAdsPlatform()
    setup_signal_handlers(platform)
    
    try:
        await platform.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
