import asyncio
import re
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Callable
from litellm import acompletion

from utils.logger import get_logger, get_logger_with_session


def check_ffmpeg_available() -> bool:
    """Check if ffmpeg is available in the system."""
    return shutil.which("ffmpeg") is not None


async def generate_narration_from_code(
    code: str,
    prompt: str,
    model: str = "cerebras/zai-glm-4.6",
    max_tokens: int = 1000,
    temperature: float = 0.7,
    session_id: Optional[str] = None
) -> List[dict]:
    """
    Generate narration segments from Manim code using LLM.

    Returns:
        List of dicts with 'text' and 'duration' keys
    """
    system_prompt = """You are an expert at creating educational narration for mathematical animations.
Analyze the provided Manim code and generate a narration script that explains what's happening in the animation.

IMPORTANT REQUIREMENTS:
1. Generate 3-5 narration segments that describe the animation chronologically
2. Each segment should be a concise, clear sentence (10-15 words ideal)
3. Focus on WHAT is being shown, not the code implementation
4. Use accessible language suitable for educational content
5. Return ONLY a JSON array with this exact format:
[
    {"text": "First narration sentence", "duration": 3.0},
    {"text": "Second narration sentence", "duration": 4.0},
    {"text": "Third narration sentence", "duration": 3.5}
]

Guidelines:
- Duration should be based on natural reading speed (about 3-5 seconds per segment)
- Total duration should roughly match the animation length
- Be descriptive but concise
- Use present tense ("We see...", "The equation transforms...", "Notice how...")

Return ONLY the JSON array, no other text."""

    user_prompt = f"""User's request: {prompt}

Generated Manim code:
```python
{code}
```

Generate the narration JSON array:"""

    response = await acompletion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )

    narration_text = response.choices[0].message.content.strip()

    # Clean up potential markdown formatting
    if narration_text.startswith("```json"):
        narration_text = narration_text[len("```json"):].strip()
    if narration_text.startswith("```"):
        narration_text = narration_text[3:].strip()
    if narration_text.endswith("```"):
        narration_text = narration_text[:-3].strip()

    # Parse the JSON response
    import json

    # Create session-aware logger if session_id provided, otherwise use default logger
    logger = get_logger_with_session("SubtitleGenerator", session_id) if session_id else get_logger("SubtitleGenerator")

    try:
        segments = json.loads(narration_text)
        # Validate structure
        if not isinstance(segments, list):
            raise ValueError("Response is not a list")
        for seg in segments:
            if not isinstance(seg, dict) or 'text' not in seg or 'duration' not in seg:
                raise ValueError("Invalid segment structure")
        return segments
    except (json.JSONDecodeError, ValueError) as e:
        # Fallback: create a single segment from the user prompt
        logger.error(f"Failed to parse LLM narration response: {e}")
        logger.error(f"Response was: {narration_text}")
        return [{"text": f"Watch this animation: {prompt[:50]}", "duration": 5.0}]


def create_srt_file(segments: List[dict], output_path: str) -> None:
    """
    Create an SRT subtitle file from narration segments.

    Args:
        segments: List of dicts with 'text' and 'duration' keys
        output_path: Path where to save the SRT file
    """
    def format_timestamp(seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    srt_content = []
    current_time = 0.0

    for idx, segment in enumerate(segments, start=1):
        start_time = current_time
        end_time = current_time + segment['duration']

        srt_content.append(f"{idx}")
        srt_content.append(f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}")
        srt_content.append(segment['text'])
        srt_content.append("")  # Empty line between segments

        current_time = end_time

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(srt_content))


async def add_subtitles_to_video(
    video_path: str,
    srt_path: str,
    output_path: str,
    subtitle_style: Optional[str] = None,
    font_size: int = 24,
    audio_path: Optional[str] = None,
    timeout: int = 300  # 5 minutes default timeout
) -> None:
    """
    Add subtitles to video using FFmpeg, optionally with audio narration.

    Args:
        video_path: Path to input video
        srt_path: Path to SRT subtitle file
        output_path: Path for output video with subtitles
        subtitle_style: Optional custom subtitle style (ASS format). If provided, font_size is ignored.
        font_size: Font size for subtitles (default: 24). Only used if subtitle_style is None.
        audio_path: Optional path to audio file to mix with video
        timeout: Maximum time in seconds to wait for FFmpeg (default: 300)

    Raises:
        RuntimeError: If ffmpeg is not available in the system
    """
    # Check if ffmpeg is available
    if not check_ffmpeg_available():
        raise RuntimeError(
            "FFmpeg is not installed or not available in PATH. "
            "Please install FFmpeg to use subtitle functionality. "
            "Visit https://ffmpeg.org/download.html for installation instructions."
        )
    # Default subtitle style - white text with black outline, bottom center
    if subtitle_style is None:
        # ASS subtitle style parameters with configurable font size
        subtitle_style = (
            f"FontName=DejaVu Sans,FontSize={font_size},PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
            "Alignment=2,MarginV=30"
        )

    # Build FFmpeg command to burn subtitles into video
    if audio_path and Path(audio_path).exists():
        # With audio: mix audio with video and burn subtitles
        logger.info(f"Adding audio from: {audio_path}")
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-i", audio_path,
            "-vf", f"subtitles={srt_path}:force_style='{subtitle_style}'",
            "-c:v", "libx264",  # Re-encode video (required for filter)
            "-c:a", "aac",      # Encode audio as AAC
            "-b:a", "192k",     # Audio bitrate
            "-shortest",        # Match shortest input duration
            "-y",               # Overwrite output file
            output_path
        ]
    else:
        # Subtitle only (original behavior)
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vf", f"subtitles={srt_path}:force_style='{subtitle_style}'",
            "-c:a", "copy",  # Copy audio stream without re-encoding
            "-y",  # Overwrite output file
            output_path
        ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    try:
        # Use communicate with timeout
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )

        if process.returncode != 0:
            stderr_str = stderr.decode() if stderr else ""
            raise Exception(f"FFmpeg subtitle addition failed (code {process.returncode}):\n{stderr_str}")

    except asyncio.TimeoutError:
        # Kill the process if it times out
        try:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        except Exception as cleanup_error:
            logger.error(f"Error during FFmpeg cleanup: {cleanup_error}")
        raise Exception(f"FFmpeg subtitle addition timeout after {timeout} seconds")

    except asyncio.CancelledError:
        # Handle cancellation gracefully
        try:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
        except Exception as cleanup_error:
            logger.error(f"Error during FFmpeg cleanup: {cleanup_error}")
        raise


async def generate_and_add_subtitles(
    video_path: str,
    code: str,
    prompt: str,
    temp_dir: str,
    model: str = "cerebras/zai-glm-4.6",
    subtitle_style: Optional[str] = None,
    font_size: int = 24,
    enable_audio: bool = False,
    audio_language: str = "EN",
    audio_speaker_id: int = 0,
    audio_speed: float = 1.0,
    progress_callback: Optional[Callable[[str, str], None]] = None,
    session_id: Optional[str] = None
) -> str:
    """
    Complete pipeline: generate narration, create SRT, optionally generate audio, add to video.

    Args:
        video_path: Path to original video
        code: Manim code that was used to generate the video
        prompt: User's original prompt
        temp_dir: Temporary directory for intermediate files
        model: LLM model to use for narration generation
        subtitle_style: Optional custom subtitle style (ASS format). If provided, font_size is ignored.
        font_size: Font size for subtitles (default: 24). Only used if subtitle_style is None.
        enable_audio: Whether to generate audio narration using TTS
        audio_language: Language code for TTS (EN, ES, FR, ZH, JP, KR)
        audio_speaker_id: Speaker voice ID for TTS
        audio_speed: Base speech speed multiplier for TTS
        progress_callback: Optional callback function(stage, message) for progress updates
        session_id: Optional session ID for logging context

    Returns:
        Path to video with subtitles (and audio if enabled)

    Raises:
        RuntimeError: If ffmpeg is not available or TTS is not available when enabled
    """
    # Create session-aware logger if session_id provided, otherwise use default logger
    logger = get_logger_with_session("SubtitleGenerator", session_id) if session_id else get_logger("SubtitleGenerator")

    def emit_progress(stage: str, message: str):
        """Helper to emit progress if callback is provided."""
        if progress_callback:
            progress_callback(stage, message)

    logger.info("Starting subtitle generation pipeline")
    logger.info(f"Video path: {video_path}")
    logger.info(f"Model: {model}")
    logger.info(f"Enable audio: {enable_audio}")
    logger.info(f"Prompt: {prompt[:100]}...")

    # Check ffmpeg availability early
    if not check_ffmpeg_available():
        raise RuntimeError(
            "FFmpeg is not installed. Subtitle generation requires FFmpeg. "
            "Please install it from https://ffmpeg.org/download.html"
        )
    logger.info("FFmpeg is available")

    # Check TTS availability if audio is enabled
    if enable_audio:
        from services.audio_generator import check_pipertts_available
        if not await check_pipertts_available():
            raise RuntimeError(
                "Piper TTS is not installed. Audio narration requires Piper TTS. "
                "Install with: pip install piper-tts"
            )
        logger.info("Piper TTS is available")

    temp_path = Path(temp_dir)

    # Generate narration segments
    emit_progress("narration", "Generating narration segments using LLM")
    logger.info("Generating narration segments using LLM...")
    segments = await generate_narration_from_code(code, prompt, model=model, session_id=session_id)
    logger.info(f"Generated {len(segments)} narration segments")
    emit_progress("narration", f"Generated {len(segments)} narration segments")

    # Create SRT file
    emit_progress("srt", "Creating SRT subtitle file")
    srt_path = temp_path / "subtitles.srt"
    logger.info(f"Creating SRT file at: {srt_path}")
    create_srt_file(segments, str(srt_path))
    logger.info("SRT file created successfully")
    emit_progress("srt", "SRT file created successfully")

    # Generate audio if enabled
    audio_path = None
    if enable_audio:
        try:
            from services.audio_generator import generate_audio_from_segments

            emit_progress("audio", "Generating audio narration using TTS")
            audio_path = temp_path / "narration.wav"
            logger.info(f"Generating audio narration at: {audio_path}")

            await generate_audio_from_segments(
                segments=segments,
                output_path=str(audio_path),
                speaker_id=audio_speaker_id,
                language=audio_language,
                base_speed=audio_speed,
                progress_callback=progress_callback,
                session_id=session_id
            )

            logger.info("Audio narration generated successfully")
            emit_progress("audio", "Audio narration generated successfully")
        except Exception as e:
            logger.error(f"Failed to generate audio narration: {e}")
            raise RuntimeError(f"Audio generation failed: {e}")

    # Add subtitles (and audio if available) to video
    if audio_path:
        emit_progress("ffmpeg", "Mixing audio and adding subtitles to video")
    else:
        emit_progress("ffmpeg", "Adding subtitles to video using FFmpeg")

    video_path_obj = Path(video_path)
    output_path = video_path_obj.parent / f"{video_path_obj.stem}_subtitled{video_path_obj.suffix}"
    logger.info("Processing video with FFmpeg...")
    logger.info(f"Input video: {video_path}")
    logger.info(f"Output video: {output_path}")
    if audio_path:
        logger.info(f"Audio file: {audio_path}")

    await add_subtitles_to_video(
        video_path,
        str(srt_path),
        str(output_path),
        subtitle_style,
        font_size,
        str(audio_path) if audio_path else None
    )

    logger.info("Video processing complete!")
    logger.info(f"Final video: {output_path}")
    return str(output_path)
