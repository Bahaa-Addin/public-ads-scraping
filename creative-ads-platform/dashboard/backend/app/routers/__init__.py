"""API Routers."""

from .jobs import router as jobs_router
from .assets import router as assets_router
from .metrics import router as metrics_router
from .scrapers import router as scrapers_router
from .logs import router as logs_router
from .health import router as health_router
from .events import router as events_router
from .screenshots import router as screenshots_router

__all__ = [
    "jobs_router",
    "assets_router", 
    "metrics_router",
    "scrapers_router",
    "logs_router",
    "health_router",
    "events_router",
    "screenshots_router",
]

