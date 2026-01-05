"""
Agent Brain - Core Orchestration Engine

The Agent Brain is the central orchestrator for the creative ads platform.
It manages scraping jobs, coordinates feature extraction, triggers reverse-prompting,
and ensures smooth pipeline execution with proper monitoring and error handling.
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
from .job_queue import JobQueue, Job, JobType, JobStatus

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
    - Trigger reverse-prompt generation via Vertex AI
    - Handle retries, throttling, and rate limits
    - Log metrics to Cloud Monitoring
    """
    
    def __init__(
        self,
        config: Config,
        job_queue: JobQueue,
        firestore: Any,  # FirestoreClient type hint avoided for circular import
    ):
        self.config = config
        self.job_queue = job_queue
        self.firestore = firestore
        
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
        for i in range(self.config.max_concurrent_jobs):
            task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._worker_tasks.append(task)
            
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(f"Agent Brain started with {self.config.max_concurrent_jobs} workers")
        
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
                await asyncio.sleep(1)
                
        logger.info(f"Worker {worker_id} stopped")
        
    async def _process_job(self, job: Job) -> None:
        """Process a single job based on its type."""
        try:
            self._active_tasks.add(job.id)
            
            handler = self.job_queue._handlers.get(job.job_type)
            if handler:
                await handler(job)
                await self.job_queue.complete(job.id)
            else:
                raise ValueError(f"No handler for job type: {job.job_type}")
                
        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}", exc_info=True)
            await self.job_queue.fail(job.id, str(e), retry=True)
            self._metrics.errors += 1
            
        finally:
            self._active_tasks.discard(job.id)
            self._metrics.last_updated = datetime.utcnow()
            
    async def _handle_scrape_job(self, job: Job) -> None:
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
                await self.job_queue.create_feature_extraction_job(
                    asset_id=asset.get("id"),
                    asset_url=asset.get("url"),
                    asset_type=asset.get("type", "image")
                )
                
            self._metrics.assets_scraped += len(assets)
            
            # Update source metrics
            if source not in self._metrics.source_metrics:
                self._metrics.source_metrics[source] = {"scraped": 0, "errors": 0}
            self._metrics.source_metrics[source]["scraped"] += len(assets)
            
        else:
            raise RuntimeError(f"Scraping failed: {result.get('error')}")
            
    async def _handle_feature_extraction_job(self, job: Job) -> None:
        """Handle a feature extraction job."""
        asset_id = job.payload.get("asset_id")
        asset_url = job.payload.get("asset_url")
        asset_type = job.payload.get("asset_type", "image")
        
        logger.info(f"Extracting features for asset: {asset_id}")
        
        # Call feature extraction module
        from feature_extraction.extract_features import FeatureExtractor
        
        extractor = FeatureExtractor()
        features = await extractor.extract(asset_url, asset_type)
        
        # Store features in Firestore
        await self.firestore.update_asset(asset_id, {"features": features})
        
        self._metrics.features_extracted += 1
        
        # Create industry classification job
        await self.job_queue.enqueue(Job(
            id=f"classify-{asset_id}",
            job_type=JobType.CLASSIFY_INDUSTRY,
            payload={
                "asset_id": asset_id,
                "features": features,
            }
        ))
        
    async def _handle_classification_job(self, job: Job) -> None:
        """Handle an industry classification job."""
        asset_id = job.payload.get("asset_id")
        features = job.payload.get("features", {})
        
        logger.info(f"Classifying industry for asset: {asset_id}")
        
        # Call classifier (stub)
        from feature_extraction.extract_features import IndustryClassifier
        
        classifier = IndustryClassifier()
        industry = await classifier.classify(features)
        
        # Update Firestore
        await self.firestore.update_asset(asset_id, {"industry": industry})
        
        # Update industry metrics
        if industry not in self._metrics.industry_metrics:
            self._metrics.industry_metrics[industry] = 0
        self._metrics.industry_metrics[industry] += 1
        
        # Create prompt generation job
        await self.job_queue.create_prompt_generation_job(
            asset_id=asset_id,
            features=features,
            industry=industry
        )
        
    async def _handle_prompt_generation_job(self, job: Job) -> None:
        """Handle a reverse-prompt generation job."""
        asset_id = job.payload.get("asset_id")
        features = job.payload.get("features", {})
        industry = job.payload.get("industry")
        
        logger.info(f"Generating reverse prompt for asset: {asset_id}")
        
        # Call Vertex AI for prompt generation
        from reverse_prompt.generate_prompt import ReversePromptGenerator
        
        generator = ReversePromptGenerator(
            project_id=self.config.gcp_project_id,
            location=self.config.vertex_ai.location if self.config.vertex_ai else "us-central1"
        )
        
        prompts = await generator.generate(
            features=features,
            industry=industry
        )
        
        # Store prompts in Firestore
        await self.firestore.update_asset(asset_id, {
            "reverse_prompt": prompts.get("positive"),
            "negative_prompt": prompts.get("negative"),
            "prompt_metadata": prompts.get("metadata"),
        })
        
        self._metrics.prompts_generated += 1
        
    async def _handle_storage_job(self, job: Job) -> None:
        """Handle an asset storage job."""
        asset_id = job.payload.get("asset_id")
        asset_data = job.payload.get("data", {})
        
        logger.info(f"Storing asset: {asset_id}")
        
        await self.firestore.store_asset(asset_id, asset_data)
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
                
            # Run scraper as subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.config.gcp_project_id  # Should be project root
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
        """Report health metrics to Cloud Monitoring."""
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
        
        logger.info(f"Health report: {json.dumps(health_data)}")
        
        # In production, send to Cloud Monitoring
        if self.config.enable_cloud_monitoring:
            await self._send_to_cloud_monitoring(health_data)
            
    async def _send_to_cloud_monitoring(self, data: Dict[str, Any]) -> None:
        """Send metrics to Google Cloud Monitoring."""
        try:
            from google.cloud import monitoring_v3
            
            client = monitoring_v3.MetricServiceClient()
            project_path = f"projects/{self.config.gcp_project_id}"
            
            # Create time series for each metric
            # This is a stub - implement full metrics in production
            logger.debug(f"Would send metrics to Cloud Monitoring: {data}")
            
        except ImportError:
            logger.debug("Cloud Monitoring client not available")
        except Exception as e:
            logger.warning(f"Failed to send metrics: {e}")
            
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
                    "max_items": task.max_items,
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
            "active_tasks": len(self._active_tasks),
            "metrics": {
                "assets_scraped": self._metrics.assets_scraped,
                "features_extracted": self._metrics.features_extracted,
                "prompts_generated": self._metrics.prompts_generated,
                "assets_stored": self._metrics.assets_stored,
                "errors": self._metrics.errors,
            },
            "queue": self.job_queue.get_metrics().__dict__,
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
        
        tasks = []
        for source in sources:
            if self.config.scrapers.get(source, {}).get("enabled", True):
                task = ScrapingTask(
                    source=source,
                    max_items=max_items_per_source,
                )
                tasks.append(task)
                
        job_ids = await self.schedule_scraping_batch(tasks)
        
        return {
            "triggered": True,
            "sources": [s.value for s in sources],
            "job_ids": job_ids,
            "total_jobs": len(job_ids),
        }

