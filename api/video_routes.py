import os
import shutil
import traceback
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from models.schemas import VideoGenerationRequest, VideoGenerationResponse
from services.code_generation import generate_manim_code
from services.video_rendering import render_manim_video

router = APIRouter(prefix="/video", tags=["video"])


@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest):
    """
    Generate a Manim video from a text prompt.

    This endpoint:
    1. Generates Manim code using an LLM based on the prompt
    2. Renders the video using Manim
    3. Returns the video file path and generated code

    Args:
        request: VideoGenerationRequest with prompt and rendering options

    Returns:
        VideoGenerationResponse with video path and metadata
    """
    temp_dir = None

    try:
        # Step 1: Generate Manim code
        generated_code, model_used = await generate_manim_code(
            prompt=request.prompt,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )

        # Step 2: Render the video
        video_path, temp_dir = await render_manim_video(
            code=generated_code,
            output_format=request.format,
            quality=request.quality,
            background_color=request.background_color
        )

        return VideoGenerationResponse(
            video_path=video_path,
            generated_code=generated_code,
            model_used=model_used,
            format=request.format,
            message="Video generated successfully! Use /video/download endpoint to retrieve it."
        )

    except Exception as e:
        # Clean up on error
        if temp_dir:
            shutil.rmtree(temp_dir, ignore_errors=True)

        raise HTTPException(
            status_code=500,
            detail=f"Error generating video: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        )


@router.get("/download")
async def download_video(video_path: str):
    """
    Download a generated video file.

    Args:
        video_path: Path to the video file (from generate-video response)

    Returns:
        FileResponse with the video file
    """
    if not os.path.exists(video_path):
        raise HTTPException(
            status_code=404,
            detail=f"Video file not found at path: {video_path}"
        )

    # Determine media type based on file extension
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
