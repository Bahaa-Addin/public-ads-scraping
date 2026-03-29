"""
Stream Manager Service

Manages live video streams from browser sessions using CDP (Chrome DevTools Protocol)
screencast. Supports multiple concurrent streams and periodic screenshot saving.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from fastapi import WebSocket

from .screenshot_saver import ScreenshotSaver

logger = logging.getLogger(__name__)


@dataclass
class StreamSession:
    """Represents an active streaming session."""
    session_id: str
    job_id: str
    source: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    last_frame_at: Optional[datetime] = None
    last_screenshot_at: Optional[datetime] = None
    frame_count: int = 0
    screenshot_count: int = 0
    current_url: Optional[str] = None
    current_action: Optional[str] = None
    cdp_session: Any = None
    is_active: bool = True


class StreamManager:
    """
    Manages live video streams and screenshot capture from browser sessions.
    
    Features:
    - CDP screencast for real-time video frames
    - WebSocket broadcasting to connected clients
    - Periodic screenshot saving for replay
    - Multiple concurrent session support
    """
    
    def __init__(
        self,
        screenshot_saver: Optional[ScreenshotSaver] = None,
        screenshot_interval_seconds: float = 2.0,
        frame_quality: int = 60,
        max_width: int = 1280,
        max_height: int = 720,
    ):
        """
        Initialize the stream manager.
        
        Args:
            screenshot_saver: ScreenshotSaver instance for saving screenshots
            screenshot_interval_seconds: Interval between saved screenshots
            frame_quality: JPEG quality for frames (1-100)
            max_width: Maximum frame width
            max_height: Maximum frame height
        """
        self.screenshot_saver = screenshot_saver or ScreenshotSaver()
        self.screenshot_interval = screenshot_interval_seconds
        self.frame_quality = frame_quality
        self.max_width = max_width
        self.max_height = max_height
        
        # Active sessions: session_id -> StreamSession
        self._sessions: Dict[str, StreamSession] = {}
        
        # WebSocket subscribers: session_id -> set of WebSocket connections
        self._subscribers: Dict[str, Set[WebSocket]] = {}
        
        # Frame callbacks for external listeners
        self._frame_callbacks: List[Callable] = []
        
        logger.info(
            f"StreamManager initialized: screenshot_interval={screenshot_interval_seconds}s, "
            f"quality={frame_quality}, resolution={max_width}x{max_height}"
        )
    
    async def start_screencast(
        self,
        session_id: str,
        job_id: str,
        page: Any,  # playwright.async_api.Page
        source: str = "unknown",
    ) -> bool:
        """
        Start CDP screencast for a Playwright page.
        
        Args:
            session_id: Unique session identifier
            job_id: Associated job ID
            page: Playwright Page object
            source: Scraper source name
            
        Returns:
            True if screencast started successfully
        """
        try:
            # Create CDP session
            cdp = await page.context.new_cdp_session(page)
            
            # Create session record
            session = StreamSession(
                session_id=session_id,
                job_id=job_id,
                source=source,
                cdp_session=cdp,
            )
            self._sessions[session_id] = session
            self._subscribers[session_id] = set()
            
            # Set up frame handler
            cdp.on("Page.screencastFrame", lambda frame: asyncio.create_task(
                self._handle_frame(session_id, frame)
            ))
            
            # Start screencast
            await cdp.send("Page.startScreencast", {
                "format": "jpeg",
                "quality": self.frame_quality,
                "maxWidth": self.max_width,
                "maxHeight": self.max_height,
                "everyNthFrame": 1,
            })
            
            logger.info(f"Started screencast for session {session_id} (job: {job_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start screencast for session {session_id}: {e}")
            return False
    
    async def stop_screencast(self, session_id: str) -> bool:
        """
        Stop screencast for a session.
        
        Args:
            session_id: The session to stop
            
        Returns:
            True if stopped successfully
        """
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        try:
            if session.cdp_session:
                await session.cdp_session.send("Page.stopScreencast")
                await session.cdp_session.detach()
            
            session.is_active = False
            
            # Notify subscribers that stream ended
            await self._broadcast_message(session_id, {
                "type": "stream_ended",
                "session_id": session_id,
                "job_id": session.job_id,
                "frame_count": session.frame_count,
                "screenshot_count": session.screenshot_count,
            })
            
            # Clean up subscribers
            for ws in list(self._subscribers.get(session_id, [])):
                try:
                    await ws.close()
                except Exception:
                    pass
            
            del self._sessions[session_id]
            if session_id in self._subscribers:
                del self._subscribers[session_id]
            
            logger.info(
                f"Stopped screencast for session {session_id}: "
                f"{session.frame_count} frames, {session.screenshot_count} screenshots"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error stopping screencast for session {session_id}: {e}")
            return False
    
    async def _handle_frame(self, session_id: str, frame: Dict[str, Any]) -> None:
        """
        Handle an incoming screencast frame.
        
        Args:
            session_id: The session that produced the frame
            frame: CDP frame data with 'data', 'metadata', 'sessionId'
        """
        session = self._sessions.get(session_id)
        if not session or not session.is_active:
            return
        
        now = datetime.utcnow()
        session.last_frame_at = now
        session.frame_count += 1
        
        frame_data = frame.get("data", "")
        metadata = frame.get("metadata", {})
        
        # Acknowledge frame to continue receiving
        if session.cdp_session:
            try:
                await session.cdp_session.send("Page.screencastFrameAck", {
                    "sessionId": frame.get("sessionId", 0)
                })
            except Exception:
                pass
        
        # Broadcast to WebSocket subscribers
        await self._broadcast_frame(session_id, frame_data, metadata)
        
        # Save screenshot periodically
        if self._should_save_screenshot(session):
            await self._save_screenshot(session, frame_data)
        
        # Notify frame callbacks
        for callback in self._frame_callbacks:
            try:
                await callback(session_id, frame_data, metadata)
            except Exception as e:
                logger.error(f"Frame callback error: {e}")
    
    def _should_save_screenshot(self, session: StreamSession) -> bool:
        """Check if we should save a screenshot based on interval."""
        if session.last_screenshot_at is None:
            return True
        
        elapsed = (datetime.utcnow() - session.last_screenshot_at).total_seconds()
        return elapsed >= self.screenshot_interval
    
    async def _save_screenshot(
        self,
        session: StreamSession,
        frame_data: str
    ) -> None:
        """Save a screenshot for the session."""
        try:
            metadata = {
                "url": session.current_url,
                "action": session.current_action,
                "step": session.screenshot_count + 1,
            }
            
            await self.screenshot_saver.save(
                session.job_id,
                frame_data,
                metadata
            )
            
            session.last_screenshot_at = datetime.utcnow()
            session.screenshot_count += 1
            
        except Exception as e:
            logger.error(f"Failed to save screenshot for session {session.session_id}: {e}")
    
    async def _broadcast_frame(
        self,
        session_id: str,
        frame_data: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Broadcast a frame to all subscribers."""
        subscribers = self._subscribers.get(session_id, set())
        if not subscribers:
            return
        
        message = {
            "type": "frame",
            "data": frame_data,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata,
        }
        
        dead_connections = []
        for ws in subscribers:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.append(ws)
        
        # Clean up dead connections
        for ws in dead_connections:
            self.unsubscribe(session_id, ws)
    
    async def _broadcast_message(
        self,
        session_id: str,
        message: Dict[str, Any]
    ) -> None:
        """Broadcast a message to all subscribers."""
        subscribers = self._subscribers.get(session_id, set())
        for ws in list(subscribers):
            try:
                await ws.send_json(message)
            except Exception:
                self.unsubscribe(session_id, ws)
    
    def subscribe(self, session_id: str, websocket: WebSocket) -> bool:
        """
        Subscribe a WebSocket to a stream session.
        
        Args:
            session_id: The session to subscribe to
            websocket: The WebSocket connection
            
        Returns:
            True if subscribed successfully
        """
        if session_id not in self._subscribers:
            self._subscribers[session_id] = set()
        
        self._subscribers[session_id].add(websocket)
        logger.debug(f"WebSocket subscribed to session {session_id}")
        return True
    
    def unsubscribe(self, session_id: str, websocket: WebSocket) -> None:
        """Unsubscribe a WebSocket from a stream session."""
        if session_id in self._subscribers:
            self._subscribers[session_id].discard(websocket)
            logger.debug(f"WebSocket unsubscribed from session {session_id}")
    
    def update_session_context(
        self,
        session_id: str,
        url: Optional[str] = None,
        action: Optional[str] = None
    ) -> None:
        """Update the current context for a session (for metadata)."""
        session = self._sessions.get(session_id)
        if session:
            if url is not None:
                session.current_url = url
            if action is not None:
                session.current_action = action
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active streaming sessions."""
        return [
            {
                "session_id": s.session_id,
                "job_id": s.job_id,
                "source": s.source,
                "started_at": s.started_at.isoformat(),
                "frame_count": s.frame_count,
                "screenshot_count": s.screenshot_count,
                "current_url": s.current_url,
                "is_active": s.is_active,
            }
            for s in self._sessions.values()
            if s.is_active
        ]
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get info about a specific session."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "job_id": session.job_id,
            "source": session.source,
            "started_at": session.started_at.isoformat(),
            "last_frame_at": session.last_frame_at.isoformat() if session.last_frame_at else None,
            "frame_count": session.frame_count,
            "screenshot_count": session.screenshot_count,
            "current_url": session.current_url,
            "current_action": session.current_action,
            "is_active": session.is_active,
            "subscriber_count": len(self._subscribers.get(session_id, [])),
        }
    
    def is_session_active(self, session_id: str) -> bool:
        """Check if a session is currently active."""
        session = self._sessions.get(session_id)
        return session is not None and session.is_active
    
    def add_frame_callback(self, callback: Callable) -> None:
        """Add a callback to be called on each frame."""
        self._frame_callbacks.append(callback)
    
    def remove_frame_callback(self, callback: Callable) -> None:
        """Remove a frame callback."""
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)
    
    async def shutdown(self) -> None:
        """Shutdown all active streams."""
        logger.info(f"Shutting down StreamManager with {len(self._sessions)} active sessions")
        
        for session_id in list(self._sessions.keys()):
            await self.stop_screencast(session_id)
        
        self._sessions.clear()
        self._subscribers.clear()
        self._frame_callbacks.clear()
