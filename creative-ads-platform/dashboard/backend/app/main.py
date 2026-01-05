"""
Creative Ads Dashboard API - Main Application

FastAPI application providing comprehensive APIs for the Creative Ads
monitoring and control dashboard.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from .config import get_settings
from .routers import (
    jobs_router,
    assets_router,
    metrics_router,
    scrapers_router,
    logs_router,
    health_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'dashboard_api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'dashboard_api_request_latency_seconds',
    'API request latency',
    ['method', 'endpoint']
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"GCP Project: {settings.gcp_project_id or 'LOCAL MODE'}")
    
    yield
    
    logger.info("Shutting down Dashboard API")


# Create FastAPI application
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="""
## Creative Ads Dashboard API

Full-stack monitoring and control dashboard for the Creative Ads Pipeline.

### Features

- **Job Management**: View, control, and monitor pipeline jobs
- **Asset Management**: Browse, filter, and export creative assets
- **Metrics & Analytics**: Real-time pipeline and system metrics
- **Scraper Control**: Trigger and monitor scrapers
- **Logs**: Search and filter application logs

### Authentication

API key authentication can be enabled via the `API_KEY` environment variable.
    """,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_request_timing(request: Request, call_next):
    """Add request timing and metrics."""
    start_time = datetime.utcnow()
    
    response = await call_next(request)
    
    # Calculate latency
    latency = (datetime.utcnow() - start_time).total_seconds()
    
    # Record metrics
    endpoint = request.url.path
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=endpoint,
        status=response.status_code
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=endpoint
    ).observe(latency)
    
    # Add timing header
    response.headers["X-Response-Time"] = f"{latency:.3f}s"
    
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Include routers
app.include_router(health_router)
app.include_router(jobs_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")
app.include_router(metrics_router, prefix="/api/v1")
app.include_router(scrapers_router, prefix="/api/v1")
app.include_router(logs_router, prefix="/api/v1")


# Prometheus metrics endpoint
@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers
    )

