"""
Session management service for storing and retrieving iterative generation sessions.
"""
from typing import Dict, Optional
from datetime import datetime
import uuid

from models.session import SessionState, IterationStatus


class SessionManager:
    """
    In-memory session storage.
    For production, this should be replaced with a database.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}

    def create_session(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        max_iterations: int = 5,
        api_token: Optional[str] = None
    ) -> SessionState:
        """
        Create a new session.

        Args:
            prompt: User's prompt
            model: LLM model to use
            temperature: Generation temperature
            max_tokens: Maximum tokens
            max_iterations: Maximum refinement iterations
            api_token: API token for the selected provider

        Returns:
            New SessionState
        """
        session_id = str(uuid.uuid4())

        session = SessionState(
            session_id=session_id,
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            max_iterations=max_iterations,
            current_iteration=0,
            status=IterationStatus.GENERATING,
            api_token=api_token
        )

        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """
        Retrieve a session by ID.

        Args:
            session_id: Session ID

        Returns:
            SessionState if found, None otherwise
        """
        return self._sessions.get(session_id)

    def update_session(self, session: SessionState) -> None:
        """
        Update an existing session.

        Args:
            session: Updated SessionState
        """
        session.updated_at = datetime.utcnow()
        self._sessions[session.session_id] = session

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> list[SessionState]:
        """
        List all sessions.

        Returns:
            List of all SessionStates
        """
        return list(self._sessions.values())

    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """
        Remove sessions older than max_age_hours.

        Args:
            max_age_hours: Maximum age in hours

        Returns:
            Number of sessions deleted
        """
        from datetime import timedelta

        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        to_delete = [
            sid for sid, session in self._sessions.items()
            if session.updated_at < cutoff_time
        ]

        for sid in to_delete:
            del self._sessions[sid]

        return len(to_delete)


# Global session manager instance
session_manager = SessionManager()
