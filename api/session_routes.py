"""
API routes for iterative session-based code generation.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
import traceback
import shutil
import json
import asyncio
from datetime import datetime

from models.session import (
    IterativeGenerationRequest,
    IterativeGenerationResponse,
    SessionStatusResponse,
    RenderRequest,
    IterationStatus,
    RenderStatus,
    RenderProgress,
    RenderStatusResponse,
    CodeIteration,
    ManualCodeUpdateRequest,
    ManualCodeUpdateResponse
)
from services.session_manager import session_manager
from services.iterative_workflow import run_iterative_generation, run_iterative_generation_streaming
from services.video_rendering import render_manim_video
from services.code_validator import validate_code
from services.session_updater import SessionUpdater
from utils.logger import get_logger

# Create logger for API routes
logger = get_logger("API")

router = APIRouter(prefix="/session", tags=["session"])


async def _render_video_background(
    session_id: str,
    code: str,
    output_format: str,
    quality: str,
    background_color: str | None,
    include_subtitles: bool,
    prompt: str,
    model: str,
    subtitle_style: str | None,
    subtitle_font_size: int,
    enable_audio: bool,
    audio_language: str,
    audio_speaker_id: int,
    audio_speed: float
):
    """Background task to render video and update session with progress using SessionUpdater."""
    temp_dir = None

    try:
        # Initialize session updater
        updater = SessionUpdater(session_id)

        # Progress callback using SessionUpdater
        def update_progress(status: str, message: str):
            """Update session with render progress."""
            try:
                updater.update_render_progress(status, message)
            except Exception as e:
                logger.error(f"Error updating render progress: {e}")

        # Mark render as started
        updater.update_render_started()
        logger.info(f"[Render {session_id}] Starting render")

        # Render the video with progress tracking
        video_path, temp_dir = await render_manim_video(
            code=code,
            output_format=output_format,
            quality=quality,
            background_color=background_color,
            include_subtitles=include_subtitles,
            prompt=prompt,
            model=model,
            subtitle_style=subtitle_style,
            subtitle_font_size=subtitle_font_size,
            enable_audio=enable_audio,
            audio_language=audio_language,
            audio_speaker_id=audio_speaker_id,
            audio_speed=audio_speed,
            progress_callback=update_progress
        )

        # Update session with success
        updater.update_render_complete(video_path)
        logger.info(f"[Render {session_id}] Completed successfully: {video_path}")

    except Exception as e:
        # Update session with error
        error_msg = str(e)
        logger.error(f"[Render {session_id}] Failed: {error_msg}")
        logger.debug(traceback.format_exc())

        try:
            updater = SessionUpdater(session_id)
            updater.update_render_error(error_msg)
        except Exception as update_error:
            logger.error(f"Failed to update session with render error: {update_error}")

        # Clean up temp directory on error
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


async def _generate_code_background(
    session_id: str,
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    max_iterations: int
):
    """Background task to run code generation and update session with progress."""
    try:
        # Initialize session updater
        updater = SessionUpdater(session_id)
        updater.update_generation_started()

        logger.info(f"[Generate {session_id}] Starting background generation")

        # Run iterative generation
        workflow_state = await run_iterative_generation(
            session_id=session_id,
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            max_iterations=max_iterations
        )

        # Update session with final results
        final_code = workflow_state.get("generated_code", "")
        status = workflow_state.get("status", IterationStatus.FAILED)

        # Update each iteration from workflow
        for iteration in workflow_state.get("iterations_history", []):
            updater.update_generation_iteration(
                iteration=iteration.iteration_number,
                status=iteration.status,
                code=iteration.generated_code,
                validation_result=iteration.validation_result,
                generation_metrics=iteration.generation_metrics,
                validation_metrics=iteration.validation_metrics
            )

        # Mark as complete
        updater.update_generation_complete(
            final_code=final_code,
            status=status
        )

        logger.info(f"[Generate {session_id}] Completed with status: {status}")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Generate {session_id}] Failed: {error_msg}")
        logger.debug(traceback.format_exc())

        try:
            updater = SessionUpdater(session_id)
            updater.update_generation_error(error_msg)
        except Exception as update_error:
            logger.error(f"Failed to update session with error: {update_error}")


@router.post("/generate", response_model=IterativeGenerationResponse)
async def start_iterative_generation(request: IterativeGenerationRequest):
    """
    Start a new iterative code generation session.

    This endpoint:
    1. Creates a new session
    2. Runs the LangGraph workflow for iterative generation and validation
    3. Returns the result with session ID for tracking

    Args:
        request: IterativeGenerationRequest with prompt and generation options

    Returns:
        IterativeGenerationResponse with session ID and results
    """
    try:
        # Create session
        session = session_manager.create_session(
            prompt=request.prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            max_iterations=request.max_iterations
        )

        logger.info(f"Created session {session.session_id}")

        # Run iterative workflow
        workflow_state = await run_iterative_generation(
            session_id=session.session_id,
            prompt=request.prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            max_iterations=request.max_iterations
        )

        # Update session with results
        session.current_iteration = workflow_state["current_iteration"]
        session.status = workflow_state["status"]
        session.iterations = workflow_state["iterations_history"]

        if workflow_state["status"] == IterationStatus.SUCCESS:
            session.final_code = workflow_state["generated_code"]

        session_manager.update_session(session)

        # Prepare response
        is_complete = workflow_state["status"] in [
            IterationStatus.SUCCESS,
            IterationStatus.MAX_ITERATIONS_REACHED
        ]

        message = ""
        if workflow_state["status"] == IterationStatus.SUCCESS:
            message = "Code generated and validated successfully!"
        elif workflow_state["status"] == IterationStatus.MAX_ITERATIONS_REACHED:
            message = f"Maximum iterations ({request.max_iterations}) reached. Code still has errors."
        else:
            message = f"Generation in progress. Current status: {workflow_state['status']}"

        return IterativeGenerationResponse(
            session_id=session.session_id,
            status=workflow_state["status"],
            current_iteration=workflow_state["current_iteration"],
            generated_code=workflow_state["generated_code"],
            validation_result=workflow_state["validation_result"],
            message=message,
            is_complete=is_complete
        )

    except Exception as e:
        logger.error(f"Error in iterative generation: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error in iterative generation: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        )


@router.post("/generate-async")
async def start_generation_async(request: IterativeGenerationRequest, background_tasks: BackgroundTasks):
    """
    Start a new iterative code generation session asynchronously (background task).

    This endpoint returns immediately with a "queued" status. The UI should either:
    - Connect to /session/{session_id}/sse for real-time updates (NDJSON stream)
    - Poll /session/status/{session_id} to track progress

    Args:
        request: IterativeGenerationRequest with prompt and generation options
        background_tasks: FastAPI background tasks

    Returns:
        Status indicating generation has been queued with session_id
    """
    try:
        # Create session
        session = session_manager.create_session(
            prompt=request.prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            max_iterations=request.max_iterations
        )

        logger.info(f"Created session {session.session_id} for async generation")

        # Start background generation task
        background_tasks.add_task(
            _generate_code_background,
            session_id=session.session_id,
            prompt=request.prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            max_iterations=request.max_iterations
        )

        return {
            "status": "queued",
            "session_id": session.session_id,
            "message": "Generation job queued. Connect to /session/{session_id}/sse for real-time updates or poll /session/status/{session_id}."
        }

    except Exception as e:
        logger.error(f"Error starting async generation: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Error starting async generation: {str(e)}"
        )


@router.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    Get the unified status of an existing session (generation + render).

    This endpoint returns complete session state including both generation
    progress and render progress. It replaces the need for separate
    /session/render-status endpoint.

    Args:
        session_id: Session ID from the generate endpoint

    Returns:
        SessionStatusResponse with full session details including render status
    """
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    return SessionStatusResponse(
        session_id=session.session_id,
        status=session.status,
        current_iteration=session.current_iteration,
        max_iterations=session.max_iterations,
        iterations_history=session.iterations,
        final_code=session.final_code,
        created_at=session.created_at,
        updated_at=session.updated_at,
        # Render fields
        render_status=session.render_status,
        render_progress=session.render_progress,
        rendered_video_path=session.rendered_video_path,
        render_error=session.render_error,
        render_started_at=session.render_started_at,
        render_completed_at=session.render_completed_at
    )


@router.get("/{session_id}/sse")
async def session_sse_stream(session_id: str):
    """
    Unified Server-Sent Events stream for session updates (NDJSON format).

    This endpoint provides real-time updates for BOTH generation and render progress
    in a single stream. The stream sends pure NDJSON (newline-delimited JSON),
    where each line is a complete JSON object followed by a newline.

    This replaces the need for separate streaming and polling endpoints.

    Event types:
    - generation_started: Generation has started
    - generation_progress: Iteration progress
    - generation_complete: Generation finished
    - generation_error: Generation failed
    - render_started: Render has started
    - render_progress: Render progress update
    - render_complete: Render finished
    - render_error: Render failed
    - session_not_found: Session doesn't exist

    Args:
        session_id: Session ID to stream updates for

    Returns:
        StreamingResponse with NDJSON stream
    """

    async def event_generator():
        """Generator for NDJSON events."""
        # Check if session exists
        session = session_manager.get_session(session_id)
        if not session:
            error_event = {
                "event": "session_not_found",
                "session_id": session_id,
                "message": f"Session {session_id} not found"
            }
            yield f"{json.dumps(error_event)}\n"
            return

        # Send initial session state
        try:
            updater = SessionUpdater(session_id)
            initial_state = updater.get_current_state()
            initial_event = {
                "event": "session_connected",
                "session_id": session_id,
                "state": initial_state
            }
            yield f"{json.dumps(initial_event)}\n"
        except Exception as e:
            logger.error(f"Error getting initial state: {e}")

        # Track last known state to detect changes
        last_state = None
        last_update_time = None

        # Stream updates (poll session for changes)
        try:
            while True:
                session = session_manager.get_session(session_id)

                if not session:
                    # Session was deleted
                    error_event = {
                        "event": "session_deleted",
                        "session_id": session_id
                    }
                    yield f"{json.dumps(error_event)}\n"
                    break

                # Get current state
                try:
                    updater = SessionUpdater(session_id)
                    current_state = updater.get_current_state()

                    # Check if state changed
                    if current_state != last_state or session.updated_at != last_update_time:
                        # Determine event type based on status changes
                        event_type = "update"

                        # Generation events
                        if session.status == IterationStatus.GENERATING:
                            event_type = "generation_progress"
                        elif session.status == IterationStatus.VALIDATING:
                            event_type = "generation_progress"
                        elif session.status == IterationStatus.REFINING:
                            event_type = "generation_progress"
                        elif session.status == IterationStatus.SUCCESS:
                            event_type = "generation_complete"
                        elif session.status == IterationStatus.MAX_ITERATIONS_REACHED:
                            event_type = "generation_complete"
                        elif session.status == IterationStatus.FAILED:
                            event_type = "generation_error"

                        # Render events (override generation if render is active)
                        if session.render_status:
                            if session.render_status == RenderStatus.QUEUED:
                                event_type = "render_queued"
                            elif session.render_status == RenderStatus.PREPARING:
                                event_type = "render_started"
                            elif session.render_status in [
                                RenderStatus.RENDERING_VIDEO,
                                RenderStatus.GENERATING_SUBTITLES,
                                RenderStatus.CREATING_SRT,
                                RenderStatus.GENERATING_AUDIO,
                                RenderStatus.MIXING_AUDIO,
                                RenderStatus.STITCHING_SUBTITLES
                            ]:
                                event_type = "render_progress"
                            elif session.render_status == RenderStatus.COMPLETED:
                                event_type = "render_complete"
                            elif session.render_status == RenderStatus.FAILED:
                                event_type = "render_error"

                        # Send update event
                        update_event = {
                            "event": event_type,
                            "session_id": session_id,
                            "timestamp": datetime.utcnow().isoformat(),
                            "state": current_state
                        }
                        yield f"{json.dumps(update_event)}\n"

                        last_state = current_state
                        last_update_time = session.updated_at

                        # Check if session is in a terminal state
                        terminal_generation = session.status in [
                            IterationStatus.SUCCESS,
                            IterationStatus.MAX_ITERATIONS_REACHED,
                            IterationStatus.FAILED
                        ]
                        terminal_render = session.render_status in [
                            RenderStatus.COMPLETED,
                            RenderStatus.FAILED,
                            None
                        ]

                        # If both generation and render are done (or render never started), we can close
                        if terminal_generation and terminal_render and session.render_status == RenderStatus.COMPLETED:
                            # Send final done event
                            done_event = {
                                "event": "done",
                                "session_id": session_id,
                                "message": "Session complete"
                            }
                            yield f"{json.dumps(done_event)}\n"
                            break

                except Exception as e:
                    logger.error(f"Error in SSE stream: {e}")
                    error_event = {
                        "event": "error",
                        "session_id": session_id,
                        "error": str(e)
                    }
                    yield f"{json.dumps(error_event)}\n"

                # Poll interval (adjust as needed)
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            # Client disconnected
            logger.info(f"SSE stream cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Fatal error in SSE stream: {e}")
            error_event = {
                "event": "fatal_error",
                "session_id": session_id,
                "error": str(e)
            }
            yield f"{json.dumps(error_event)}\n"

    return StreamingResponse(
        event_generator(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/render")
async def render_session_code(request: RenderRequest, background_tasks: BackgroundTasks):
    """
    Start rendering the validated code from a successful session (async).

    This endpoint returns immediately with a "queued" status. The UI should poll
    /session/render-status/{session_id} to track progress.

    Args:
        request: RenderRequest with session_id and rendering options
        background_tasks: FastAPI background tasks

    Returns:
        Status indicating render has been queued
    """
    session = session_manager.get_session(request.session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {request.session_id} not found"
        )

    if not session.final_code:
        raise HTTPException(
            status_code=400,
            detail="Session has no validated code to render. Generate code first."
        )

    # Check if already rendering
    if session.render_status and session.render_status not in [RenderStatus.COMPLETED, RenderStatus.FAILED]:
        raise HTTPException(
            status_code=409,
            detail=f"Render already in progress with status: {session.render_status}"
        )

    # Initialize render status
    session.render_status = RenderStatus.QUEUED
    session.render_progress = [RenderProgress(
        status=RenderStatus.QUEUED,
        message="Render job queued",
        timestamp=datetime.utcnow()
    )]
    session.render_started_at = None
    session.render_completed_at = None
    session.render_error = None
    session_manager.update_session(session)

    # Start background render task
    background_tasks.add_task(
        _render_video_background,
        session_id=request.session_id,
        code=session.final_code,
        output_format=request.format,
        quality=request.quality,
        background_color=request.background_color,
        include_subtitles=request.include_subtitles,
        prompt=session.prompt,
        model=request.model,
        subtitle_style=request.subtitle_style,
        subtitle_font_size=request.subtitle_font_size,
        enable_audio=request.enable_audio,
        audio_language=request.audio_language,
        audio_speaker_id=request.audio_speaker_id,
        audio_speed=request.audio_speed
    )

    return {
        "status": "queued",
        "session_id": request.session_id,
        "message": "Render job queued. Connect to /session/{session_id}/sse for real-time updates or poll /session/status/{session_id}."
    }


@router.get("/download")
async def download_session_video(session_id: str):
    """
    Download a rendered video from a session.

    Args:
        session_id: Session ID (video must be rendered first)

    Returns:
        FileResponse with the video file
    """
    import os
    from pathlib import Path

    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    # Check if video has been rendered
    if not session.rendered_video_path:
        raise HTTPException(
            status_code=404,
            detail=f"No rendered video found for session {session_id}. Render the video first using /session/render endpoint."
        )

    video_path = session.rendered_video_path

    if not os.path.exists(video_path):
        raise HTTPException(
            status_code=404,
            detail=f"Video file not found at path: {video_path}. It may have been deleted."
        )

    # Determine media type
    ext = Path(video_path).suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".gif": "image/gif",
        ".mov": "video/quicktime"
    }

    media_type = media_types.get(ext, "application/octet-stream")
    filename = f"manim_video_{session_id[:8]}{ext}"

    return FileResponse(
        path=video_path,
        media_type=media_type,
        filename=filename
    )


@router.get("/stream")
async def stream_session_video(session_id: str):
    """
    Stream a rendered video from a session for playback in the UI.

    This endpoint supports HTTP range requests for seeking and progressive playback.

    Args:
        session_id: Session ID (video must be rendered first)

    Returns:
        StreamingResponse with the video file
    """
    import os
    from pathlib import Path

    # Get session
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    # Check if video has been rendered
    if not session.rendered_video_path:
        raise HTTPException(
            status_code=404,
            detail=f"No rendered video found for session {session_id}. Render the video first using /session/render endpoint."
        )

    video_path = session.rendered_video_path

    if not os.path.exists(video_path):
        raise HTTPException(
            status_code=404,
            detail=f"Video file not found at path: {video_path}. It may have been deleted."
        )

    # Determine media type
    ext = Path(video_path).suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".gif": "image/gif",
        ".mov": "video/quicktime"
    }

    media_type = media_types.get(ext, "video/mp4")

    # Return file response for streaming (supports range requests automatically)
    return FileResponse(
        path=video_path,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache"
        }
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session.

    Args:
        session_id: Session ID to delete

    Returns:
        Success message
    """
    success = session_manager.delete_session(session_id)

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    return {"message": f"Session {session_id} deleted successfully"}


@router.get("/list")
async def list_sessions():
    """
    List all sessions.

    Returns:
        List of session summaries
    """
    sessions = session_manager.list_sessions()

    return {
        "count": len(sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "prompt": s.prompt[:100] + "..." if len(s.prompt) > 100 else s.prompt,
                "status": s.status,
                "current_iteration": s.current_iteration,
                "max_iterations": s.max_iterations,
                "created_at": s.created_at,
                "updated_at": s.updated_at
            }
            for s in sessions
        ]
    }


@router.post("/update-code", response_model=ManualCodeUpdateResponse)
async def update_session_code_manually(request: ManualCodeUpdateRequest):
    """
    Manually update and validate code in an existing session.

    This allows users to fix code after max iterations is reached or to make
    manual improvements. The code can be validated before being saved to the session.

    Args:
        request: ManualCodeUpdateRequest with session_id and edited code

    Returns:
        ManualCodeUpdateResponse with validation results
    """
    session = session_manager.get_session(request.session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {request.session_id} not found"
        )

    validation_result = None
    is_valid = False

    # Validate if requested
    if request.should_validate:
        try:
            validation_result = await validate_code(request.code, dry_run=True)
            is_valid = validation_result.get("is_valid", False)

            # Create a new iteration record for the manual edit
            manual_iteration = CodeIteration(
                iteration_number=session.current_iteration + 1,
                generated_code=request.code,
                validation_result=validation_result,
                timestamp=datetime.utcnow(),
                status=IterationStatus.SUCCESS if is_valid else IterationStatus.FAILED
            )

            # Add to session history
            session.iterations.append(manual_iteration)
            session.current_iteration += 1

            # Update final code if valid
            if is_valid:
                session.final_code = request.code
                session.status = IterationStatus.SUCCESS
            else:
                session.status = IterationStatus.FAILED

            session_manager.update_session(session)

            message = "Code validated and updated successfully!" if is_valid else "Code updated but validation failed. Check errors."

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error validating code: {str(e)}"
            )
    else:
        # Update without validation
        session.final_code = request.code
        session_manager.update_session(session)
        message = "Code updated without validation"

    return ManualCodeUpdateResponse(
        session_id=request.session_id,
        code=request.code,
        validation_result=validation_result,
        is_valid=is_valid,
        message=message
    )
