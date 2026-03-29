"""
Health API Router

Endpoints for health checks and service status.
"""

from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends
import asyncio

from ..models import HealthResponse, ServiceHealth
from ..config import get_settings, Settings

router = APIRouter(tags=["Health"])

# Track startup time
_start_time = datetime.utcnow()


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Comprehensive health check endpoint.
    
    Checks connectivity to all dependent services.
    """
    services = await _check_services(settings)
    
    # Overall status
    all_healthy = all(s.healthy for s in services)
    status = "healthy" if all_healthy else "degraded"
    
    uptime = (datetime.utcnow() - _start_time).total_seconds()
    
    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        uptime_seconds=uptime,
        services=services
    )


@router.get("/ready")
async def readiness_check(settings: Settings = Depends(get_settings)):
    """
    Kubernetes readiness probe.
    
    Returns 200 if the service is ready to receive traffic.
    """
    # Quick check - just verify we can respond
    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe.
    
    Returns 200 if the service is alive.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


async def _check_services(settings: Settings) -> List[ServiceHealth]:
    """Check health of all dependent services."""
    checks = [
        _check_firestore(settings),
        _check_pubsub(settings),
        _check_agent_service(settings),
        _check_scraper_service(settings),
    ]
    
    results = await asyncio.gather(*checks, return_exceptions=True)
    
    services = []
    for result in results:
        if isinstance(result, Exception):
            services.append(ServiceHealth(
                name="unknown",
                healthy=False,
                last_check=datetime.utcnow(),
                message=str(result)
            ))
        else:
            services.append(result)
    
    return services


async def _check_firestore(settings: Settings) -> ServiceHealth:
    """Check Firestore connectivity."""
    start = datetime.utcnow()
    healthy = True
    message = None
    
    if not settings.gcp_project_id:
        return ServiceHealth(
            name="firestore",
            healthy=True,
            latency_ms=0,
            last_check=datetime.utcnow(),
            message="Running in local/mock mode"
        )
    
    try:
        from google.cloud import firestore
        client = firestore.AsyncClient(project=settings.gcp_project_id)
        # Simple connectivity check
        await asyncio.wait_for(
            client.collection("_health_check").limit(1).get(),
            timeout=5.0
        )
    except asyncio.TimeoutError:
        healthy = False
        message = "Connection timeout"
    except Exception as e:
        healthy = False
        message = str(e)
    
    latency = (datetime.utcnow() - start).total_seconds() * 1000
    
    return ServiceHealth(
        name="firestore",
        healthy=healthy,
        latency_ms=latency,
        last_check=datetime.utcnow(),
        message=message
    )


async def _check_pubsub(settings: Settings) -> ServiceHealth:
    """Check Pub/Sub connectivity."""
    start = datetime.utcnow()
    healthy = True
    message = None
    
    if not settings.gcp_project_id:
        return ServiceHealth(
            name="pubsub",
            healthy=True,
            latency_ms=0,
            last_check=datetime.utcnow(),
            message="Running in local/mock mode"
        )
    
    try:
        from google.cloud import pubsub_v1
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(settings.gcp_project_id, settings.pubsub_topic)
        # Check topic exists (this is synchronous)
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: publisher.get_topic(request={"topic": topic_path})
        )
    except Exception as e:
        healthy = False
        message = str(e)
    
    latency = (datetime.utcnow() - start).total_seconds() * 1000
    
    return ServiceHealth(
        name="pubsub",
        healthy=healthy,
        latency_ms=latency,
        last_check=datetime.utcnow(),
        message=message
    )


async def _check_agent_service(settings: Settings) -> ServiceHealth:
    """Check Agent service connectivity."""
    import httpx
    
    start = datetime.utcnow()
    healthy = True
    message = None
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.agent_api_url}/health")
            if response.status_code != 200:
                healthy = False
                message = f"HTTP {response.status_code}"
    except httpx.ConnectError:
        healthy = False
        message = "Connection refused"
    except httpx.TimeoutException:
        healthy = False
        message = "Connection timeout"
    except Exception as e:
        healthy = False
        message = str(e)
    
    latency = (datetime.utcnow() - start).total_seconds() * 1000
    
    return ServiceHealth(
        name="agent_service",
        healthy=healthy,
        latency_ms=latency,
        last_check=datetime.utcnow(),
        message=message
    )


async def _check_scraper_service(settings: Settings) -> ServiceHealth:
    """Check Scraper service connectivity."""
    import httpx
    
    start = datetime.utcnow()
    healthy = True
    message = None
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.scraper_api_url}/health")
            if response.status_code != 200:
                healthy = False
                message = f"HTTP {response.status_code}"
    except httpx.ConnectError:
        healthy = False
        message = "Connection refused (may be expected in dev)"
    except httpx.TimeoutException:
        healthy = False
        message = "Connection timeout"
    except Exception as e:
        healthy = False
        message = str(e)
    
    latency = (datetime.utcnow() - start).total_seconds() * 1000
    
    return ServiceHealth(
        name="scraper_service",
        healthy=healthy,
        latency_ms=latency,
        last_check=datetime.utcnow(),
        message=message
    )

