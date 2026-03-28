"""Context and session management (Phase 4)."""
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class SessionManager:
    """Session and context manager for user interactions."""

    def __init__(self, max_history: int = 100):
        """
        Initialize session manager.

        Args:
            max_history: Maximum history items per session.
        """
        self.sessions: Dict[str, Dict] = {}
        self.max_history = max_history
        logger.info(f"SessionManager initialized (max_history={max_history})")

    async def get_or_create_session(self, session_id: str) -> Dict:
        """
        Get or create a session.

        Args:
            session_id: Unique session identifier.

        Returns:
            Session dictionary.
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "id": session_id,
                "created_at": datetime.now(),
                "last_accessed": datetime.now(),
                "request_history": [],
                "preferences": {
                    "language": None,
                    "region": None,
                    "units": "metric"  # metric or imperial
                },
                "state": {},
                "stats": {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "cache_hits": 0
                }
            }
            logger.info(f"Created new session: {session_id[:8]}...")

        # Update last accessed
        self.sessions[session_id]["last_accessed"] = datetime.now()
        return self.sessions[session_id]

    async def add_request(
        self,
        session_id: str,
        request_type: str,
        input_data: Dict,
        output_data: Dict,
        success: bool = True,
        duration_ms: float = 0.0
    ):
        """
        Add a request to session history.

        Args:
            session_id: Session identifier.
            request_type: Type of request (e.g., "extract_destination").
            input_data: Request input.
            output_data: Request output.
            success: Whether request succeeded.
            duration_ms: Request duration in milliseconds.
        """
        session = await self.get_or_create_session(session_id)

        request_record = {
            "timestamp": datetime.now(),
            "type": request_type,
            "input": input_data,
            "output": output_data,
            "success": success,
            "duration_ms": round(duration_ms, 2)
        }

        # Add to history
        session["request_history"].append(request_record)

        # Limit history size
        if len(session["request_history"]) > self.max_history:
            session["request_history"] = session["request_history"][-self.max_history:]

        # Update stats
        session["stats"]["total_requests"] += 1
        if success:
            session["stats"]["successful_requests"] += 1
        else:
            session["stats"]["failed_requests"] += 1

        logger.info(
            f"Added request to session {session_id[:8]}... "
            f"(type={request_type}, success={success})"
        )

    async def update_preference(
        self,
        session_id: str,
        key: str,
        value: Any
    ):
        """
        Update user preference.

        Args:
            session_id: Session identifier.
            key: Preference key.
            value: Preference value.
        """
        session = await self.get_or_create_session(session_id)
        session["preferences"][key] = value
        logger.info(f"Updated preference {key}={value} for session {session_id[:8]}...")

    async def get_preferences(self, session_id: str) -> Dict:
        """
        Get user preferences.

        Args:
            session_id: Session identifier.

        Returns:
            Preferences dictionary.
        """
        session = await self.get_or_create_session(session_id)
        return session["preferences"]

    async def set_state(
        self,
        session_id: str,
        key: str,
        value: Any
    ):
        """
        Set session state.

        Args:
            session_id: Session identifier.
            key: State key.
            value: State value.
        """
        session = await self.get_or_create_session(session_id)
        session["state"][key] = value
        logger.debug(f"Set state {key} for session {session_id[:8]}...")

    async def get_state(self, session_id: str, key: str = None) -> Any:
        """
        Get session state.

        Args:
            session_id: Session identifier.
            key: State key (optional, returns all if None).

        Returns:
            State value or entire state dict.
        """
        session = await self.get_or_create_session(session_id)
        if key:
            return session["state"].get(key)
        return session["state"]

    async def get_history(
        self,
        session_id: str,
        limit: int = 10,
        request_type: str = None
    ) -> List[Dict]:
        """
        Get request history.

        Args:
            session_id: Session identifier.
            limit: Maximum number of records.
            request_type: Filter by request type (optional).

        Returns:
            List of request records.
        """
        session = await self.get_or_create_session(session_id)
        history = session["request_history"]

        if request_type:
            history = [r for r in history if r["type"] == request_type]

        return history[-limit:]

    async def get_stats(self, session_id: str) -> Dict:
        """
        Get session statistics.

        Args:
            session_id: Session identifier.

        Returns:
            Statistics dictionary.
        """
        session = await self.get_or_create_session(session_id)
        return {
            **session["stats"],
            "session_age_seconds": (
                datetime.now() - session["created_at"]
            ).total_seconds(),
            "history_size": len(session["request_history"])
        }

    async def clear_session(self, session_id: str):
        """
        Clear a session.

        Args:
            session_id: Session identifier.
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared session: {session_id[:8]}...")

    async def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """
        Clean up expired sessions.

        Args:
            max_age_hours: Maximum session age in hours.
        """
        now = datetime.now()
        expired = []

        for session_id, session in self.sessions.items():
            age = (now - session["last_accessed"]).total_seconds() / 3600
            if age > max_age_hours:
                expired.append(session_id)

        for session_id in expired:
            del self.sessions[session_id]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

    def get_active_sessions_count(self) -> int:
        """Get number of active sessions."""
        return len(self.sessions)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
