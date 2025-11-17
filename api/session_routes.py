"""
API routes for iterative session-based code generation.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import traceback
import shutil

from models.session import (
    IterativeGenerationRequest,
    IterativeGenerationResponse,
    SessionStatusResponse,
    RenderRequest,
    IterationStatus,
    CodeIteration
)
from services.session_manager import session_manager
from services.iterative_workflow import run_iterative_generation
from services.video_rendering import render_manim_video

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

        print(f"\n[API] Created session {session.session_id}")

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
