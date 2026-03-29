"""
Events API Router

Server-Sent Events (SSE) endpoint for real-time pipeline monitoring.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["Events"])


# ==========================================================================
# Event Models
# ==========================================================================

class PipelineEvent(BaseModel):
    """A pipeline event for real-time monitoring."""
    type: str  # Event type
    data: Dict[str, Any]  # Event data
    timestamp: str  # ISO timestamp
    job_id: Optional[str] = None  # Associated job ID


# ==========================================================================
# Global Event Queue
# ==========================================================================

# Global queue for SSE events
# In production, this would use Redis pub/sub or similar
_event_queues: list = []
_event_history: list = []
MAX_HISTORY = 100


async def emit_event(
    event_type: str,
    data: Dict[str, Any],
    job_id: Optional[str] = None
):
    """
    Emit an event to all connected SSE clients.
    
    Event types:
    - pipeline_started: Full pipeline began
    - step_started: Individual step began
    - step_progress: Progress update with percentage
    - asset_scraped: New asset scraped (includes preview)
    - screenshot_captured: Screenshot taken (includes URL)
    - features_extracted: Features computed for asset
    - prompt_generated: Prompt created for asset
    - step_completed: Step finished with results
    - pipeline_completed: Full pipeline finished
    - error: Error occurred
    """
    event = PipelineEvent(
        type=event_type,
        data=data,
        timestamp=datetime.utcnow().isoformat(),
        job_id=job_id
    )
    
    # Add to history
    _event_history.append(event)
    if len(_event_history) > MAX_HISTORY:
        _event_history.pop(0)
    
    # Send to all connected clients
    for queue in _event_queues:
        try:
            await queue.put(event)
        except Exception as e:
            logger.warning(f"Failed to send event to queue: {e}")


def get_recent_events(limit: int = 50) -> list:
    """Get recent events from history."""
    return list(reversed(_event_history[-limit:]))


# ==========================================================================
# SSE Endpoint
# ==========================================================================

@router.get("/stream")
async def event_stream(request: Request, include_history: bool = True):
    """
    Server-Sent Events stream for real-time pipeline updates.
    
    Connect to this endpoint to receive real-time events:
    ```javascript
    const eventSource = new EventSource('/api/v1/events/stream');
    eventSource.onmessage = (e) => {
        const event = JSON.parse(e.data);
        console.log(event.type, event.data);
    };
    ```
    
    Query params:
    - include_history: If true, sends recent event history on connect (default: true)
    """
    async def generate():
        queue = asyncio.Queue()
        _event_queues.append(queue)
        
        try:
            # Send initial connection event
            yield f"data: {json.dumps({'type': 'connected', 'data': {'message': 'Connected to event stream'}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
            
            # Send recent event history so clients don't miss events when navigating
            if include_history and _event_history:
                for event in _event_history[-20:]:  # Last 20 events
                    yield f"data: {event.model_dump_json()}\n\n"
            
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                try:
                    # Wait for event with timeout
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat', 'data': {}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"
        finally:
            _event_queues.remove(queue)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/history")
async def get_event_history(limit: int = 50):
    """Get recent event history."""
    events = get_recent_events(limit)
    return {
        "events": [e.model_dump() for e in events],
        "count": len(events)
    }


@router.post("/emit")
async def emit_custom_event(
    event_type: str,
    data: Dict[str, Any] = {},
    job_id: Optional[str] = None
):
    """
    Emit a custom event (for agent/scraper integration).
    
    This endpoint allows the agent and scrapers to push events
    to the SSE stream for real-time dashboard updates.
    """
    await emit_event(event_type, data, job_id)
    return {"status": "ok", "message": f"Event '{event_type}' emitted"}


@router.get("/status")
async def get_stream_status():
    """Get status of the event stream."""
    return {
        "connected_clients": len(_event_queues),
        "history_size": len(_event_history),
        "max_history": MAX_HISTORY
    }
