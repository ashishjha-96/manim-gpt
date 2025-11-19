"""
Unified callable structure for session updates.
Provides consistent update methods for both generation and render progress.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from models.session import (
    IterationStatus,
    RenderStatus,
    RenderProgress,
    CodeIteration,
    ValidationMetrics,
    GenerationMetrics
)
from services.session_manager import session_manager
from utils.logger import get_logger

logger = get_logger("SessionUpdater")


class SessionUpdater:
    """
    Unified callable structure for all session updates.
    Handles both generation and render progress updates consistently.
    """

    def __init__(self, session_id: str):
        """
        Initialize updater for a specific session.

        Args:
            session_id: The session ID to update
        """
        self.session_id = session_id
        self.session = session_manager.get_session(session_id)

        if not self.session:
            raise ValueError(f"Session {session_id} not found")

    # ==================== Generation Updates ====================

    def update_generation_started(self) -> None:
        """Mark generation as started."""
        self.session = session_manager.get_session(self.session_id)
        if not self.session:
            return

        self.session.status = IterationStatus.GENERATING
        self.session.current_iteration = 0
        session_manager.update_session(self.session)
        logger.info(f"[{self.session_id}] Generation started")

    def update_generation_iteration(
        self,
        iteration: int,
        status: IterationStatus,
        code: Optional[str] = None,
        validation_result: Optional[Dict[str, Any]] = None,
        generation_metrics: Optional[GenerationMetrics] = None,
        validation_metrics: Optional[ValidationMetrics] = None
    ) -> None:
        """
        Update session with iteration progress.

        Args:
            iteration: Current iteration number
            status: Current iteration status
            code: Generated code (if available)
            validation_result: Validation result (if available)
            generation_metrics: Generation metrics (tokens, time, etc.)
            validation_metrics: Validation metrics (errors, warnings, etc.)
        """
        self.session = session_manager.get_session(self.session_id)
        if not self.session:
            return

        self.session.current_iteration = iteration
        self.session.status = status

        if code:
            self.session.generated_code = code

        # Add to iterations history
        if code or validation_result:
            iteration_record = CodeIteration(
                iteration_number=iteration,
                generated_code=code or "",
                validation_result=validation_result,
                timestamp=datetime.utcnow(),
                status=status,
                generation_metrics=generation_metrics,
                validation_metrics=validation_metrics
            )

            # Update or append iteration
            existing_idx = next(
                (i for i, it in enumerate(self.session.iterations)
                 if it.iteration_number == iteration),
                None
            )

            if existing_idx is not None:
                self.session.iterations[existing_idx] = iteration_record
            else:
                self.session.iterations.append(iteration_record)

        session_manager.update_session(self.session)
        logger.info(f"[{self.session_id}] Iteration {iteration}: {status}")

    def update_generation_complete(
        self,
        final_code: str,
        status: IterationStatus,
        message: Optional[str] = None
    ) -> None:
        """
        Mark generation as complete.

        Args:
            final_code: The final generated code
            status: Final status (SUCCESS or MAX_ITERATIONS_REACHED)
            message: Optional completion message
        """
        self.session = session_manager.get_session(self.session_id)
        if not self.session:
            return

        self.session.status = status
        self.session.final_code = final_code if status == IterationStatus.SUCCESS else None

        session_manager.update_session(self.session)
        logger.info(f"[{self.session_id}] Generation complete: {status}")

    def update_generation_error(self, error_message: str) -> None:
        """
        Mark generation as failed with error.

        Args:
            error_message: Error message
        """
        self.session = session_manager.get_session(self.session_id)
        if not self.session:
            return

        self.session.status = IterationStatus.FAILED
        self.session.error_message = error_message

        session_manager.update_session(self.session)
        logger.error(f"[{self.session_id}] Generation error: {error_message}")

    # ==================== Render Updates ====================

    def update_render_started(self) -> None:
        """Mark render as started."""
        self.session = session_manager.get_session(self.session_id)
        if not self.session:
            return

        self.session.render_status = RenderStatus.PREPARING
        self.session.render_started_at = datetime.utcnow()
        self.session.render_progress = [RenderProgress(
            status=RenderStatus.PREPARING,
            message="Starting video render",
            timestamp=datetime.utcnow()
        )]
        self.session.render_error = None
        self.session.render_completed_at = None

        session_manager.update_session(self.session)
        logger.info(f"[{self.session_id}] Render started")

    def update_render_progress(self, status: str, message: str) -> None:
        """
        Update render progress.

        Args:
            status: Render status string
            message: Progress message
        """
        self.session = session_manager.get_session(self.session_id)
        if not self.session:
            return

        # Map status string to RenderStatus enum
        try:
            render_status = RenderStatus(status)
        except ValueError:
            # If status doesn't match enum, default to rendering_video
            render_status = RenderStatus.RENDERING_VIDEO

        self.session.render_status = render_status
        self.session.render_progress.append(RenderProgress(
            status=render_status,
            message=message,
            timestamp=datetime.utcnow()
        ))

        session_manager.update_session(self.session)
        logger.info(f"[{self.session_id}] Render progress: {status} - {message}")

    def update_render_complete(self, video_path: str) -> None:
        """
        Mark render as complete.

        Args:
            video_path: Path to rendered video
        """
        self.session = session_manager.get_session(self.session_id)
        if not self.session:
            return

        self.session.rendered_video_path = video_path
        self.session.render_status = RenderStatus.COMPLETED
        self.session.render_completed_at = datetime.utcnow()
        self.session.render_progress.append(RenderProgress(
            status=RenderStatus.COMPLETED,
            message="Video rendered successfully",
            timestamp=datetime.utcnow()
        ))

        session_manager.update_session(self.session)
        logger.info(f"[{self.session_id}] Render complete: {video_path}")

    def update_render_error(self, error_message: str) -> None:
        """
        Mark render as failed with error.

        Args:
            error_message: Error message
        """
        self.session = session_manager.get_session(self.session_id)
        if not self.session:
            return

        self.session.render_status = RenderStatus.FAILED
        self.session.render_error = error_message
        self.session.render_completed_at = datetime.utcnow()
        self.session.render_progress.append(RenderProgress(
            status=RenderStatus.FAILED,
            message=f"Render failed: {error_message}",
            timestamp=datetime.utcnow(),
            error=error_message
        ))

        session_manager.update_session(self.session)
        logger.error(f"[{self.session_id}] Render error: {error_message}")

    # ==================== Unified State ====================

    def get_current_state(self) -> Dict[str, Any]:
        """
        Get current session state for SSE/polling.

        Returns:
            Dict with complete session state
        """
        self.session = session_manager.get_session(self.session_id)
        if not self.session:
            return {"error": "Session not found"}

        return {
            "session_id": self.session.session_id,
            "status": self.session.status,
            "current_iteration": self.session.current_iteration,
            "max_iterations": self.session.max_iterations,
            "generated_code": self.session.generated_code,
            "final_code": self.session.final_code,
            "iterations_history": [
                {
                    "iteration_number": it.iteration_number,
                    "status": it.status,
                    "generated_code": it.generated_code,
                    "validation_result": it.validation_result,
                    "timestamp": it.timestamp.isoformat() if it.timestamp else None,
                }
                for it in self.session.iterations
            ],
            "render_status": self.session.render_status,
            "render_progress": [
                {
                    "status": p.status,
                    "message": p.message,
                    "timestamp": p.timestamp.isoformat() if p.timestamp else None,
                    "error": p.error
                }
                for p in self.session.render_progress
            ] if self.session.render_progress else [],
            "rendered_video_path": self.session.rendered_video_path,
            "render_error": self.session.render_error,
            "created_at": self.session.created_at.isoformat() if self.session.created_at else None,
            "updated_at": self.session.updated_at.isoformat() if self.session.updated_at else None,
        }
