"""
Agent Brain - Core Orchestration Engine

The Agent Brain is the central orchestrator for the creative ads platform.
It manages scraping jobs, coordinates feature extraction, triggers reverse-prompting,
and ensures smooth pipeline execution with proper monitoring and error handling.

IMPORTANT: This module ONLY imports interfaces, never cloud SDKs directly.
Adapters are injected at runtime by the Orchestrator.
"""

import asyncio
import logging
import subprocess
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from .config import Config, ScraperSource, IndustryCategory
from .interfaces import (
    StorageInterface,
    QueueInterface,
    LLMInterface,
    MonitoringInterface,
)
from .interfaces.queue import JobData, JobType, JobStatus
from .interfaces.monitoring import LogLevel

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Stages in the creative ads processing pipeline."""
    SCRAPING = "scraping"
    FEATURE_EXTRACTION = "feature_extraction"
    INDUSTRY_CLASSIFICATION = "industry_classification"
    REVERSE_PROMPTING = "reverse_prompting"
    STORAGE = "storage"


@dataclass
class ScrapingTask:
    """Represents a scraping task configuration."""
    source: ScraperSource
    query: Optional[str] = None
    filters: Dict[str, Any] = field(default_factory=dict)
    max_items: int = 100
    industry_hint: Optional[IndustryCategory] = None


@dataclass
class PipelineMetrics:
    """Metrics for pipeline monitoring."""
    assets_scraped: int = 0
    features_extracted: int = 0
    prompts_generated: int = 0
    assets_stored: int = 0
    errors: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    # Per-source metrics
    source_metrics: Dict[str, Dict[str, int]] = field(default_factory=dict)
    
    # Per-industry metrics
    industry_metrics: Dict[str, int] = field(default_factory=dict)


class AgentBrain:
    """
    Central orchestration engine for the creative ads platform.
    
    Responsibilities:
    - Dispatch scraping jobs to Node.js Playwright scrapers
    - Coordinate feature extraction pipeline
    - Trigger reverse-prompt generation
    - Handle retries, throttling, and rate limits
    - Log metrics to monitoring
    
    IMPORTANT: This class receives adapters through dependency injection.
    It NEVER imports cloud SDKs directly - all operations go through interfaces.
    """
    
    def __init__(
        self,
        config: Config,
        job_queue: QueueInterface,
        storage: StorageInterface,
        llm: LLMInterface,
        monitoring: MonitoringInterface,
    ):
        """
        Initialize Agent Brain with injected adapters.
        
        Args:
            config: Platform configuration
            job_queue: Queue interface (local or cloud)
            storage: Storage interface (local or cloud)
            llm: LLM interface (local templates or cloud Vertex AI)
            monitoring: Monitoring interface (local or cloud)
        """
        self.config = config
        self.job_queue = job_queue
        self.storage = storage
        self.llm = llm
        self.monitoring = monitoring
        
        # Pipeline state
        self._running = False
        self._active_tasks: Set[str] = set()
        self._metrics = PipelineMetrics()
        
        # Rate limiting
        self._rate_limiters: Dict[ScraperSource, asyncio.Semaphore] = {}
        self._last_request_times: Dict[ScraperSource, datetime] = {}
        
        # Task management
        self._worker_tasks: List[asyncio.Task] = []
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Initialize rate limiters for each source
        self._init_rate_limiters()
        
    def _init_rate_limiters(self) -> None:
        """Initialize rate limiters for each scraper source."""
        for source, scraper_config in self.config.scrapers.items():
            # Semaphore limits concurrent requests per source
            max_concurrent = scraper_config.rate_limit_requests_per_minute // 10
            self._rate_limiters[source] = asyncio.Semaphore(max(1, max_concurrent))
            
    async def start(self) -> None:
        """Start the agent brain processing loop."""
        logger.info("Starting Agent Brain...")
        self._running = True
        
        # Register job handlers
        self.job_queue.register_handler(JobType.SCRAPE, self._handle_scrape_job)
        self.job_queue.register_handler(JobType.EXTRACT_FEATURES, self._handle_feature_extraction_job)
        self.job_queue.register_handler(JobType.GENERATE_PROMPT, self._handle_prompt_generation_job)
        self.job_queue.register_handler(JobType.CLASSIFY_INDUSTRY, self._handle_classification_job)
        self.job_queue.register_handler(JobType.STORE_ASSET, self._handle_storage_job)
        
        # Start worker tasks
        num_workers = min(self.config.max_concurrent_jobs, self.config.low_ram.max_concurrent_scrapes)
        for i in range(num_workers):
            task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._worker_tasks.append(task)
            
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        await self.monitoring.log(
            LogLevel.INFO,
            f"Agent Brain started with {num_workers} workers",
            {"mode": self.config.mode.value}
        )
        
        logger.info(f"Agent Brain started with {num_workers} workers")
        
    async def stop(self) -> None:
        """Stop the agent brain gracefully."""
        logger.info("Stopping Agent Brain...")
        self._running = False
        
        # Cancel all worker tasks
        for task in self._worker_tasks:
            task.cancel()
            
        if self._health_check_task:
            self._health_check_task.cancel()
            
        # Wait for tasks to complete
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        await self.monitoring.log(LogLevel.INFO, "Agent Brain stopped")
        logger.info("Agent Brain stopped")
        
    async def _worker_loop(self, worker_id: str) -> None:
        """Main worker loop for processing jobs."""
        logger.info(f"Worker {worker_id} started")
        
        while self._running:
            try:
                job = await self.job_queue.dequeue(timeout_seconds=5.0)
                
                if job is None:
                    await asyncio.sleep(1)
                    continue
                    
                logger.debug(f"Worker {worker_id} processing job: {job.id}")
                await self._process_job(job)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
                await self.monitoring.log_error(e, {"worker_id": worker_id})
                await asyncio.sleep(1)
                
        logger.info(f"Worker {worker_id} stopped")
        
    async def _process_job(self, job: JobData) -> None:
        """Process a single job based on its type."""
        start_time = datetime.utcnow()
        
        try:
            self._active_tasks.add(job.id)
            
            handler = self.job_queue._handlers.get(job.job_type)
            if handler:
                await handler(job)
                await self.job_queue.complete(job.id)
                
                # Record success
                duration = (datetime.utcnow() - start_time).total_seconds()
                await self.monitoring.record_pipeline_event(
                    stage=job.job_type.value,
                    event_type="completed",
                    duration_seconds=duration,
                    success=True
                )
            else:
                raise ValueError(f"No handler for job type: {job.job_type}")
                
        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}", exc_info=True)
            await self.job_queue.fail(job.id, str(e), retry=True)
            self._metrics.errors += 1
            
            # Record failure
            duration = (datetime.utcnow() - start_time).total_seconds()
            await self.monitoring.record_pipeline_event(
                stage=job.job_type.value,
                event_type="failed",
                duration_seconds=duration,
                success=False,
                metadata={"error": str(e)}
            )
            
        finally:
            self._active_tasks.discard(job.id)
            self._metrics.last_updated = datetime.utcnow()
            
    async def _handle_scrape_job(self, job: JobData) -> None:
        """Handle a scraping job by dispatching to Node.js scraper."""
        source = job.payload.get("source")
        query = job.payload.get("query")
        filters = job.payload.get("filters", {})
        
        logger.info(f"Processing scrape job for source: {source}")
        
        # Rate limiting
        source_enum = ScraperSource(source) if source else ScraperSource.META_AD_LIBRARY
        await self._apply_rate_limit(source_enum)
        
        # Dispatch to Node.js scraper
        result = await self._call_node_scraper(source, query, filters)
        
        if result.get("success"):
            assets = result.get("assets", [])
            logger.info(f"Scraped {len(assets)} assets from {source}")
            
            # Create feature extraction jobs for each asset
            for asset in assets:
                # Store asset first
                await self.storage.store_asset(
                    asset_id=asset.get("id"),
                    data=asset
                )
                
                # Then create feature extraction job
                await self.job_queue.create_feature_extraction_job(
                    asset_id=asset.get("id"),
                    asset_url=asset.get("url") or asset.get("imageUrl", ""),
                    asset_type=asset.get("type", "image")
                )
                
            self._metrics.assets_scraped += len(assets)
            
            # Update source metrics
            if source not in self._metrics.source_metrics:
                self._metrics.source_metrics[source] = {"scraped": 0, "errors": 0}
            self._metrics.source_metrics[source]["scraped"] += len(assets)
            
            # Record metrics
            await self.monitoring.increment_counter(
                f"source_{source}_scraped",
                len(assets)
            )
            
        else:
            raise RuntimeError(f"Scraping failed: {result.get('error')}")
            
    async def _handle_feature_extraction_job(self, job: JobData) -> None:
        """Handle a feature extraction job."""
        asset_id = job.payload.get("asset_id")
        asset_url = job.payload.get("asset_url")
        asset_type = job.payload.get("asset_type", "image")
        
        logger.info(f"Extracting features for asset: {asset_id}")
        
        # Import feature extractor (no cloud deps)
        from feature_extraction.extract_features import FeatureExtractor
        
        extractor = FeatureExtractor()
        features = await extractor.extract(asset_url, asset_type)
        
        # Store features using storage interface
        await self.storage.update_asset(asset_id, {"features": features})
        
        self._metrics.features_extracted += 1
        
        # Create industry classification job
        await self.job_queue.enqueue(JobData(
            id=f"classify-{asset_id}",
            job_type=JobType.CLASSIFY_INDUSTRY,
            payload={
                "asset_id": asset_id,
                "features": features,
            }
        ))
        
    async def _handle_classification_job(self, job: JobData) -> None:
        """Handle an industry classification job."""
        asset_id = job.payload.get("asset_id")
        features = job.payload.get("features", {})
        
        logger.info(f"Classifying industry for asset: {asset_id}")
        
        # Import classifier (no cloud deps)
        from feature_extraction.extract_features import IndustryClassifier
        
        classifier = IndustryClassifier()
        industry = await classifier.classify(features)
        
        # Update storage
        await self.storage.update_asset(asset_id, {"industry": industry})
        
        # Update industry metrics
        if industry not in self._metrics.industry_metrics:
            self._metrics.industry_metrics[industry] = 0
        self._metrics.industry_metrics[industry] += 1
        
        await self.monitoring.increment_counter(f"industry_{industry}")
        
        # Create prompt generation job
        await self.job_queue.create_prompt_generation_job(
            asset_id=asset_id,
            features=features,
            industry=industry
        )
        
    async def _handle_prompt_generation_job(self, job: JobData) -> None:
        """Handle a reverse-prompt generation job."""
        asset_id = job.payload.get("asset_id")
        features = job.payload.get("features", {})
        industry = job.payload.get("industry")
        
        logger.info(f"Generating reverse prompt for asset: {asset_id}")
        
        # Use injected LLM interface (handles local vs cloud automatically)
        prompt_result = await self.llm.generate_prompt(
            features=features,
            industry=industry
        )
        
        # Store prompts using storage interface
        await self.storage.update_asset(asset_id, {
            "reverse_prompt": prompt_result.positive,
            "negative_prompt": prompt_result.negative,
            "prompt_metadata": prompt_result.metadata,
        })
        
        self._metrics.prompts_generated += 1
        
        await self.monitoring.increment_counter("prompts_generated")
        
    async def _handle_storage_job(self, job: JobData) -> None:
        """Handle an asset storage job."""
        asset_id = job.payload.get("asset_id")
        asset_data = job.payload.get("data", {})
        
        logger.info(f"Storing asset: {asset_id}")
        
        await self.storage.store_asset(asset_id, asset_data)
        self._metrics.assets_stored += 1
        
    async def _call_node_scraper(
        self,
        source: str,
        query: Optional[str],
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call the Node.js Playwright scraper subprocess."""
        try:
            cmd = [
                "node",
                "scrapers/scraper.js",
                "--source", source,
            ]
            
            if query:
                cmd.extend(["--query", query])
                
            if filters:
                cmd.extend(["--filters", json.dumps(filters)])
            
            # Apply low-RAM limits
            max_items = min(
                filters.get("maxItems", 100),
                self.config.low_ram.global_job_cap
            )
            cmd.extend(["--max-items", str(max_items)])
                
            # Run scraper as subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.job_timeout_seconds
            )
            
            if process.returncode != 0:
                logger.error(f"Scraper error: {stderr.decode()}")
                return {"success": False, "error": stderr.decode()}
                
            result = json.loads(stdout.decode())
            return {"success": True, **result}
            
        except asyncio.TimeoutError:
            return {"success": False, "error": "Scraper timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _apply_rate_limit(self, source: ScraperSource) -> None:
        """Apply rate limiting for a specific source."""
        semaphore = self._rate_limiters.get(source)
        if not semaphore:
            return
            
        async with semaphore:
            # Check time since last request
            last_time = self._last_request_times.get(source)
            if last_time:
                config = self.config.scrapers.get(source)
                if config:
                    min_interval = 60.0 / config.rate_limit_requests_per_minute
                    elapsed = (datetime.utcnow() - last_time).total_seconds()
                    if elapsed < min_interval:
                        await asyncio.sleep(min_interval - elapsed)
                        
            self._last_request_times[source] = datetime.utcnow()
            
    async def _health_check_loop(self) -> None:
        """Periodic health check and metrics reporting."""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval_seconds)
                await self._report_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
                
    async def _report_health(self) -> None:
        """Report health metrics to monitoring."""
        queue_metrics = self.job_queue.get_metrics()
        
        health_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "active_tasks": len(self._active_tasks),
            "queue_size": self.job_queue.get_queue_size(),
            "pipeline_metrics": {
                "assets_scraped": self._metrics.assets_scraped,
                "features_extracted": self._metrics.features_extracted,
                "prompts_generated": self._metrics.prompts_generated,
                "errors": self._metrics.errors,
            },
            "queue_metrics": {
                "total_jobs": queue_metrics.total_jobs,
                "pending_jobs": queue_metrics.pending_jobs,
                "completed_jobs": queue_metrics.completed_jobs,
                "failed_jobs": queue_metrics.failed_jobs,
            },
            "source_metrics": self._metrics.source_metrics,
            "industry_metrics": self._metrics.industry_metrics,
        }
        
        await self.monitoring.log(LogLevel.INFO, "Health report", health_data)
        
        # Report health status
        from .interfaces.monitoring import HealthStatus
        
        await self.monitoring.report_health(HealthStatus(
            healthy=self._metrics.errors < 10,
            components={
                "queue": queue_metrics.failed_jobs < queue_metrics.total_jobs * 0.1,
                "storage": True,  # Assume healthy if no exceptions
                "llm": self.llm.is_available(),
            },
            details=health_data
        ))
            
    # Public API methods
    
    async def schedule_scraping_batch(
        self,
        tasks: List[ScrapingTask]
    ) -> List[str]:
        """Schedule a batch of scraping tasks."""
        job_ids = []
        
        for task in tasks:
            job_id = await self.job_queue.create_scrape_job(
                source=task.source.value,
                query=task.query,
                filters={
                    **task.filters,
                    "max_items": min(task.max_items, self.config.low_ram.global_job_cap),
                    "industry_hint": task.industry_hint.value if task.industry_hint else None,
                },
                priority=1 if task.industry_hint else 0
            )
            job_ids.append(job_id)
            
        logger.info(f"Scheduled {len(job_ids)} scraping tasks")
        return job_ids
        
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "running": self._running,
            "mode": self.config.mode.value,
            "active_tasks": len(self._active_tasks),
            "metrics": {
                "assets_scraped": self._metrics.assets_scraped,
                "features_extracted": self._metrics.features_extracted,
                "prompts_generated": self._metrics.prompts_generated,
                "assets_stored": self._metrics.assets_stored,
                "errors": self._metrics.errors,
            },
            "queue": {
                "size": self.job_queue.get_queue_size(),
                **self.job_queue.get_metrics().__dict__
            },
            "last_updated": self._metrics.last_updated.isoformat(),
        }
        
    async def trigger_full_pipeline(
        self,
        sources: Optional[List[ScraperSource]] = None,
        industries: Optional[List[IndustryCategory]] = None,
        max_items_per_source: int = 100
    ) -> Dict[str, Any]:
        """Trigger a full pipeline run across specified sources."""
        sources = sources or list(ScraperSource)
        
        # Apply job cap
        max_items = min(max_items_per_source, self.config.low_ram.global_job_cap)
        
        tasks = []
        for source in sources:
            scraper_config = self.config.scrapers.get(source)
            if scraper_config and scraper_config.enabled:
                task = ScrapingTask(
                    source=source,
                    max_items=max_items,
                )
                tasks.append(task)
                
        job_ids = await self.schedule_scraping_batch(tasks)
        
        return {
            "triggered": True,
            "mode": self.config.mode.value,
            "sources": [s.value for s in sources],
            "job_ids": job_ids,
            "total_jobs": len(job_ids),
        }


# Import os for path operations
import os
