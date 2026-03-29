"""
NormClaim — Notifications Router
Provides notification retrieval for the frontend dashboard.
"""

from typing import List, Dict, Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from services.auth import require_user

router = APIRouter(prefix="/api", tags=["Notifications"])
# Dashboard (`notifications.js`) connects to `ws://…:8000/notifications` (no /api prefix).
ws_router = APIRouter(tags=["Notifications"])


@ws_router.websocket("/notifications")
async def notifications_websocket(websocket: WebSocket):
    """
    Stub WebSocket for live notifications. Accepts connections from the dashboard;
    push events can be added when a backend pub/sub exists.
    """
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    except RuntimeError as exc:
        # Starlette raises if receive() is called after disconnect was already delivered.
        if "disconnect" not in str(exc).lower():
            raise


@router.get("/notifications", response_model=List[Dict[str, Any]])
async def get_notifications(current_user: dict = Depends(require_user)):
    """
    Return notifications for the authenticated user.

    Currently returns an empty list — will be backed by a persistent
    notification store (Supabase table or Redis) in a future iteration.
    """
    # TODO: Query notifications from DB filtered by current_user["id"]
    return []
