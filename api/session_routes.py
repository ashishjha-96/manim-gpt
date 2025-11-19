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
    """Background task to render video and update session with progress."""
    session = session_manager.get_session(session_id)
    if not session:
        logger.error(f"Session {session_id} not found during background render")
        return

    temp_dir = None

    def update_progress(status: str, message: str):
        """Update session with render progress."""
        nonlocal session
        try:
            # Map status string to RenderStatus enum
            try:
                render_status = RenderStatus(status)
            except ValueError:
                # If status doesn't match enum, default to rendering_video
                render_status = RenderStatus.RENDERING_VIDEO

            session.render_status = render_status
            session.render_progress.append(RenderProgress(
                status=render_status,
                message=message,
                timestamp=datetime.utcnow()
            ))
            session_manager.update_session(session)
            logger.info(f"[Render {session_id}] {status}: {message}")
        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    try:
        # Mark render as started
        session.render_status = RenderStatus.PREPARING
        session.render_started_at = datetime.utcnow()
        session.render_progress = [RenderProgress(
            status=RenderStatus.PREPARING,
            message="Starting video render",
            timestamp=datetime.utcnow()
        )]
        session_manager.update_session(session)

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
        session.rendered_video_path = video_path
        session.render_status = RenderStatus.COMPLETED
        session.render_completed_at = datetime.utcnow()
        session.render_progress.append(RenderProgress(
            status=RenderStatus.COMPLETED,
            message="Video rendered successfully",
            timestamp=datetime.utcnow()
        ))
        session_manager.update_session(session)

        logger.info(f"[Render {session_id}] Completed successfully: {video_path}")

    except Exception as e:
        # Update session with error
        error_msg = str(e)
        logger.error(f"[Render {session_id}] Failed: {error_msg}")
        logger.debug(traceback.format_exc())

        session.render_status = RenderStatus.FAILED
        session.render_error = error_msg
        session.render_completed_at = datetime.utcnow()
        session.render_progress.append(RenderProgress(
            status=RenderStatus.FAILED,
            message=f"Render failed: {error_msg}",
            timestamp=datetime.utcnow(),
            error=error_msg
        ))
        session_manager.update_session(session)

        # Clean up temp directory on error
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)


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


@router.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(session_id: str):
    """
    Get the status of an existing session.

    Args:
        session_id: Session ID from the generate endpoint

    Returns:
        SessionStatusResponse with full session details
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
        updated_at=session.updated_at
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
        "message": "Render job queued. Poll /session/render-status/{session_id} for progress."
    }


@router.get("/render-status/{session_id}", response_model=RenderStatusResponse)
async def get_render_status(session_id: str):
    """
    Get the current render status for a session.

    Use this endpoint to poll for render progress after calling /session/render.

    Args:
        session_id: Session ID

    Returns:
        RenderStatusResponse with current render status and progress
    """
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    # Calculate elapsed time if render has started
    elapsed_time = None
    if session.render_started_at:
        end_time = session.render_completed_at or datetime.utcnow()
        elapsed_time = (end_time - session.render_started_at).total_seconds()

    return RenderStatusResponse(
        session_id=session_id,
        render_status=session.render_status or RenderStatus.QUEUED,
        progress=session.render_progress,
        video_path=session.rendered_video_path,
        started_at=session.render_started_at,
        completed_at=session.render_completed_at,
        error=session.render_error,
        elapsed_time=elapsed_time
    )


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


@router.post("/generate-stream")
async def start_iterative_generation_stream(request: IterativeGenerationRequest):
    """
    Start a new iterative code generation session with Server-Sent Events streaming.

    This endpoint streams real-time progress updates including:
    - Each iteration's generated code
    - Validation results and errors
    - Current status and progress

    Returns a stream of JSON objects with progress updates.
    """

    async def event_generator():
        """Generator for Server-Sent Events."""
        try:
            # Create session
            session = session_manager.create_session(
                prompt=request.prompt,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                max_iterations=request.max_iterations
            )

            logger.info(f"[Streaming] Created session {session.session_id}")

            # Stream workflow progress
            async for progress_data in run_iterative_generation_streaming(
                session_id=session.session_id,
                prompt=request.prompt,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                max_iterations=request.max_iterations
            ):
                # Update session with latest progress
                if progress_data.get("event") == "progress" or progress_data.get("event") == "complete":
                    session.current_iteration = progress_data.get("current_iteration", 0)
                    session.status = progress_data.get("status", IterationStatus.GENERATING)

                    # Update iterations history
                    iterations_history = progress_data.get("iterations_history", [])
                    session.iterations = [
                        CodeIteration(
                            iteration_number=iter_data["iteration_number"],
                            generated_code=iter_data["generated_code"],
                            validation_result=iter_data["validation_result"],
                            timestamp=datetime.fromisoformat(iter_data["timestamp"]),
                            status=iter_data["status"]
                        )
                        for iter_data in iterations_history
                    ]

                    # Update final code if successful
                    if session.status == IterationStatus.SUCCESS:
                        session.final_code = progress_data.get("generated_code")

                    session_manager.update_session(session)

                # Send SSE event
                yield f"data: {json.dumps(progress_data)}\n\n"

            # Send final done event
            yield f"data: {json.dumps({'event': 'done', 'session_id': session.session_id})}\n\n"

        except Exception as e:
            logger.error(f"[Streaming] Error: {str(e)}")
            logger.debug(traceback.format_exc())
            error_data = {
                "event": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


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
