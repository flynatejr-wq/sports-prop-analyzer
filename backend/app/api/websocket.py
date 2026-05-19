"""
WebSocket endpoint — pushes live prop updates and alerts to connected clients.
Clients subscribe to a JSON stream; server broadcasts whenever props refresh.
"""
import asyncio
import json
import logging
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.utils.cache import cache

logger = logging.getLogger(__name__)
router = APIRouter()

# Connected WebSocket clients
_clients: Set[WebSocket] = set()


async def broadcast(message: dict):
    """Send a message to all connected WebSocket clients."""
    if not _clients:
        return
    payload = json.dumps(message, default=str)
    dead: Set[WebSocket] = set()
    for ws in _clients.copy():
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    _clients.difference_update(dead)


@router.websocket("/live")
async def live_feed(websocket: WebSocket):
    """
    WebSocket feed — streams prop updates every 30 seconds.
    Client receives JSON: {type: "props_update", data: [...props]}
    """
    await websocket.accept()
    _clients.add(websocket)
    logger.info("WS client connected — total: %d", len(_clients))

    try:
        # Send initial snapshot
        top_props = await cache.get("top_props") or []
        await websocket.send_text(json.dumps({"type": "snapshot", "data": top_props}, default=str))

        # Keep connection alive; server pushes updates via broadcast()
        while True:
            try:
                # Heartbeat — listen for ping or client messages
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if data == "ping":
                    await websocket.send_text('{"type":"pong"}')
            except asyncio.TimeoutError:
                # Send periodic snapshot even without client message
                top_props = await cache.get("top_props") or []
                await websocket.send_text(
                    json.dumps({"type": "props_update", "data": top_props[:25]}, default=str)
                )

    except WebSocketDisconnect:
        logger.info("WS client disconnected")
    except Exception as exc:
        logger.warning("WS error: %s", exc)
    finally:
        _clients.discard(websocket)


@router.websocket("/alerts")
async def alert_stream(websocket: WebSocket):
    """
    Dedicated WebSocket for real-time alert notifications only.
    """
    await websocket.accept()
    _clients.add(websocket)
    try:
        while True:
            await asyncio.sleep(60)
            await websocket.send_text('{"type":"heartbeat"}')
    except WebSocketDisconnect:
        pass
    finally:
        _clients.discard(websocket)
