"""Session and context API routes (Phase 4)."""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Header
from pydantic import BaseModel

from app.monitoring.session_manager import get_session_manager
from app.monitoring.metrics import track_request_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/session", tags=["session-context"])


# Request/Response models
class PreferenceUpdateRequest(BaseModel):
    """Preference update request."""
    key: str
    value: str


class StateUpdateRequest(BaseModel):
    """State update request."""
    key: str
    value: str


# Helper to extract session ID from header
def get_session_id(x_session_id: Optional[str] = Header(None)) -> str:
    """Extract or generate session ID."""
    if x_session_id:
        return x_session_id
    return "default-session"


# API endpoints
@router.get(
    "/stats",
    summary="Get session statistics",
    description="Get statistics for current session"
)
@track_request_metrics('get_session_stats')
async def get_session_stats(
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """Get session statistics."""
    try:
        session_id = get_session_id(x_session_id)
        manager = get_session_manager()
        stats = await manager.get_stats(session_id)

        return {
            "session_id": session_id[:8] + "...",
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Failed to get session stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session statistics"
        )


@router.get(
    "/history",
    summary="Get request history",
    description="Get request history for current session"
)
@track_request_metrics('get_session_history')
async def get_session_history(
    limit: int = 10,
    request_type: Optional[str] = None,
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """Get request history."""
    try:
        session_id = get_session_id(x_session_id)
        manager = get_session_manager()
        history = await manager.get_history(
            session_id,
            limit=limit,
            request_type=request_type
        )

        return {
            "session_id": session_id[:8] + "...",
            "history": [
                {
                    **record,
                    "timestamp": record["timestamp"].isoformat()
                }
                for record in history
            ],
            "total": len(history)
        }

    except Exception as e:
        logger.error(f"Failed to get session history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session history"
        )


@router.get(
    "/preferences",
    summary="Get user preferences",
    description="Get user preferences for current session"
)
@track_request_metrics('get_session_preferences')
async def get_session_preferences(
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """Get user preferences."""
    try:
        session_id = get_session_id(x_session_id)
        manager = get_session_manager()
        preferences = await manager.get_preferences(session_id)

        return {
            "session_id": session_id[:8] + "...",
            "preferences": preferences
        }

    except Exception as e:
        logger.error(f"Failed to get preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get preferences"
        )


@router.put(
    "/preferences",
    summary="Update user preference",
    description="Update a user preference for current session"
)
@track_request_metrics('update_session_preference')
async def update_session_preference(
    request: PreferenceUpdateRequest,
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """Update user preference."""
    try:
        session_id = get_session_id(x_session_id)
        manager = get_session_manager()
        await manager.update_preference(
            session_id,
            request.key,
            request.value
        )

        return {
            "session_id": session_id[:8] + "...",
            "key": request.key,
            "value": request.value,
            "status": "updated"
        }

    except Exception as e:
        logger.error(f"Failed to update preference: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preference"
        )


@router.get(
    "/state",
    summary="Get session state",
    description="Get session state for current session"
)
@track_request_metrics('get_session_state')
async def get_session_state(
    key: Optional[str] = None,
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """Get session state."""
    try:
        session_id = get_session_id(x_session_id)
        manager = get_session_manager()
        state = await manager.get_state(session_id, key=key)

        return {
            "session_id": session_id[:8] + "...",
            "state": state
        }

    except Exception as e:
        logger.error(f"Failed to get state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get state"
        )


@router.put(
    "/state",
    summary="Update session state",
    description="Update a session state key"
)
@track_request_metrics('update_session_state')
async def update_session_state(
    request: StateUpdateRequest,
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """Update session state."""
    try:
        session_id = get_session_id(x_session_id)
        manager = get_session_manager()
        await manager.set_state(
            session_id,
            request.key,
            request.value
        )

        return {
            "session_id": session_id[:8] + "...",
            "key": request.key,
            "value": request.value,
            "status": "updated"
        }

    except Exception as e:
        logger.error(f"Failed to update state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update state"
        )


@router.delete(
    "",
    summary="Clear session",
    description="Clear current session data"
)
@track_request_metrics('clear_session')
async def clear_session(
    x_session_id: str = Header(None, alias="X-Session-ID")
):
    """Clear session."""
    try:
        session_id = get_session_id(x_session_id)
        manager = get_session_manager()
        await manager.clear_session(session_id)

        return {
            "session_id": session_id[:8] + "...",
            "status": "cleared"
        }

    except Exception as e:
        logger.error(f"Failed to clear session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear session"
        )


@router.get(
    "/admin/active-count",
    summary="Get active sessions count",
    description="Get number of active sessions (admin)"
)
@track_request_metrics('get_active_sessions_count')
async def get_active_sessions_count():
    """Get active sessions count."""
    try:
        manager = get_session_manager()
        count = manager.get_active_sessions_count()

        return {
            "active_sessions": count
        }

    except Exception as e:
        logger.error(f"Failed to get active sessions count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active sessions count"
        )
