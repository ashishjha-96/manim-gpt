"""
API routes for iterative session-based code generation.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import traceback
import shutil
import json
from datetime import datetime

from models.session import (
    IterativeGenerationRequest,
    IterativeGenerationResponse,
    SessionStatusResponse,
    RenderRequest,
    IterationStatus,
    CodeIteration,
    ManualCodeUpdateRequest,
    ManualCodeUpdateResponse
)
from services.session_manager import session_manager
from services.iterative_workflow import run_iterative_generation, run_iterative_generation_streaming
from services.video_rendering import render_manim_video
from services.code_validator import validate_code
from utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)

router = APIRouter(prefix="/session", tags=["session"])


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

        logger.info(
            "Session created for code generation",
            extra={
                'session_id': session.session_id,
                'model': request.model,
                'max_iterations': request.max_iterations,
                'temperature': request.temperature
            }
        )

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
async def render_session_code(request: RenderRequest):
    """
    Render the validated code from a successful session.

    Args:
        request: RenderRequest with session_id and rendering options

    Returns:
        Video path and metadata
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

    temp_dir = None

    try:
        # Render the video
        video_path, temp_dir = await render_manim_video(
            code=session.final_code,
            output_format=request.format,
            quality=request.quality,
            background_color=request.background_color
        )

        return {
            "session_id": request.session_id,
            "video_path": video_path,
            "format": request.format,
            "quality": request.quality,
            "message": "Video rendered successfully! Use /session/download endpoint to retrieve it."
        }

    except Exception as e:
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

        raise HTTPException(
            status_code=500,
            detail=f"Error rendering video: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        )


@router.get("/download")
async def download_session_video(video_path: str):
    """
    Download a rendered video from a session.

    Args:
        video_path: Path to the video file (from render endpoint)

    Returns:
        FileResponse with the video file
    """
    import os
    from pathlib import Path

    if not os.path.exists(video_path):
        raise HTTPException(
            status_code=404,
            detail=f"Video file not found at path: {video_path}"
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
    filename = f"manim_video{ext}"

    return FileResponse(
        path=video_path,
        media_type=media_type,
        filename=filename
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

            logger.info(
                "Session created for streaming code generation",
                extra={
                    'session_id': session.session_id,
                    'model': request.model,
                    'max_iterations': request.max_iterations,
                    'temperature': request.temperature,
                    'streaming': True
                }
            )

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
