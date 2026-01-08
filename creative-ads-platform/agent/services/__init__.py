"""
Agent Services

Provides specialized services for the agent:
- StreamManager: Live browser streaming via CDP screencast
- ScreenshotSaver: Screenshot storage for job replay
"""

from .stream_manager import StreamManager
from .screenshot_saver import ScreenshotSaver

__all__ = [
    "StreamManager",
    "ScreenshotSaver",
]
