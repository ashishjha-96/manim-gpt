import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional, Callable

from utils.constants import QUALITY_PRESETS
from utils.logger import get_logger, get_logger_with_session


async def render_manim_video(
    code: str,
    output_format: str,
    quality: str,
    background_color: Optional[str] = None,
    include_subtitles: bool = False,
    prompt: Optional[str] = None,
    model: Optional[str] = "cerebras/zai-glm-4.6",
    subtitle_style: Optional[str] = None,
    subtitle_font_size: int = 24,
    enable_audio: bool = False,
    audio_language: str = "EN",
    audio_speaker_id: int = 0,
    audio_speed: float = 1.0,
    progress_callback: Optional[Callable[[str, str], None]] = None,
    timeout: int = 600,  # 10 minutes default timeout
    session_id: Optional[str] = None
) -> tuple[str, str]:
    """
    Render a Manim video from the generated code.

    Args:
        code: Manim Python code
        output_format: Video format (mp4, webm, gif, mov)
        quality: Quality preset (low, medium, high, 4k)
        background_color: Optional background color
        include_subtitles: Whether to generate and add subtitles
        prompt: User's original prompt (needed for subtitle generation)
        model: LLM model for subtitle generation
        subtitle_style: Optional custom subtitle style (ASS format). If provided, subtitle_font_size is ignored.
        subtitle_font_size: Font size for subtitles (default: 24)
        enable_audio: Whether to generate audio narration using TTS
        audio_language: Language code for TTS (EN, ES, FR, ZH, JP, KR)
        audio_speaker_id: Speaker voice ID for TTS
        audio_speed: Base speech speed multiplier for TTS
        progress_callback: Optional callback function(status, message) for progress updates
        timeout: Maximum time in seconds to wait for rendering (default: 600)
        session_id: Optional session ID for logging context

    Returns:
        tuple: (video_path, temp_dir)
    """
    # Create session-aware logger if session_id provided, otherwise use default logger
    logger = get_logger_with_session("VideoRendering", session_id) if session_id else get_logger("VideoRendering")
    def emit_progress(status: str, message: str):
        """Helper to emit progress if callback is provided."""
        if progress_callback:
            progress_callback(status, message)

    # Create temporary directory for the Manim project
    temp_dir = tempfile.mkdtemp(prefix="manim_")
    process = None

    try:
        emit_progress("preparing", "Setting up rendering environment")
        # Set up fontconfig to find fonts in Nix store
        # This fixes the "white boxes" issue where text doesn't render
        fontconfig_dir = Path(temp_dir) / "fontconfig"
        fontconfig_dir.mkdir()
        fontconfig_path = fontconfig_dir / "fonts.conf"

        with open(fontconfig_path, "w") as f:
            f.write("""<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <!-- DejaVu fonts from Nix store -->
  <dir>/nix/store/1mjlla0fc468wl9cphnn2ivpfx02mr7j-dejavu-fonts-minimal-2.37/share/fonts</dir>
  <cachedir>~/.cache/fontconfig</cachedir>
</fontconfig>
""")

        # Create media directories that Manim expects
        media_dir = Path(temp_dir) / "media"
        media_dir.mkdir(exist_ok=True)
        (media_dir / "Tex").mkdir(exist_ok=True)
        (media_dir / "images").mkdir(exist_ok=True)
        (media_dir / "text").mkdir(exist_ok=True)
        (media_dir / "videos").mkdir(exist_ok=True)

        # Write the generated code to a Python file
        script_path = Path(temp_dir) / "scene.py"
        with open(script_path, "w") as f:
            f.write(code)

        # Create manim config file if background color is specified
        if background_color:
            config_path = Path(temp_dir) / "manim.cfg"
            with open(config_path, "w") as f:
                f.write(f"[CLI]\nbackground_color = {background_color}\n")

        # Get quality settings
        quality_settings = QUALITY_PRESETS[quality]

        # Build manim command using current Python interpreter
        cmd = [
            sys.executable, "-m", "manim",
            "render",
            str(script_path),
            "GeneratedScene",
            "-q", quality_settings['quality_flag'],
            "-o", f"output.{output_format}",
            "--format", output_format,
        ]

        # Set up environment variables for font rendering
        env = os.environ.copy()
        env['FONTCONFIG_FILE'] = str(fontconfig_path)

        # Run manim rendering
        emit_progress("rendering_video", "Rendering Manim animation")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=temp_dir,
            env=env
        )

        # Stream output in real-time
        stdout_lines = []
        stderr_lines = []

        async def read_stream(stream, is_stderr=False):
            """Read stream line by line and log output."""
            lines = stderr_lines if is_stderr else stdout_lines

            while True:
                line = await stream.readline()
                if not line:
                    break

                decoded_line = line.decode().rstrip()
                lines.append(decoded_line)

                # Log all output
                if decoded_line:
                    logger.info(decoded_line)

        # Read both streams concurrently with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    read_stream(process.stdout, is_stderr=False),
                    read_stream(process.stderr, is_stderr=True)
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Rendering process exceeded timeout of {timeout}s")
            raise Exception(f"Video rendering timeout after {timeout} seconds")

        # Wait for process to complete
        await process.wait()
        emit_progress("rendering_video", "Manim rendering completed")

        # Decode output for debugging
        stdout_str = "\n".join(stdout_lines)
        stderr_str = "\n".join(stderr_lines)

        if process.returncode != 0:
            raise Exception(f"Manim rendering failed (code {process.returncode}):\nSTDOUT: {stdout_str}\nSTDERR: {stderr_str}")

        # Find the output video file - try multiple possible locations
        # Manim output path structure: media/videos/<scriptname>/<quality>/<filename>
        quality_dirs = {
            "l": "480p15",
            "m": "720p30",
            "h": "1080p60",
            "p": "1440p60",
            "k": "2160p60"
        }
        quality_dir = quality_dirs.get(quality_settings['quality_flag'], "720p30")

        possible_paths = [
            Path(temp_dir) / "media" / "videos" / "scene" / quality_dir / f"output.{output_format}",
            Path(temp_dir) / "media" / "videos" / "scene" / f"output.{output_format}",
            Path(temp_dir) / "media" / "videos" / f"output.{output_format}",
            Path(temp_dir) / "media" / f"output.{output_format}",
        ]

        # Also search for any files with the right extension
        media_dir = Path(temp_dir) / "media"
        if media_dir.exists():
            found_files = list(media_dir.rglob(f"*.{output_format}"))
            if found_files:
                video_path = found_files[0]
            else:
                video_path = None
        else:
            video_path = None

        # Try predefined paths if search didn't work
        if not video_path or not video_path.exists():
            for path in possible_paths:
                if path.exists():
                    video_path = path
                    break

        if not video_path or not video_path.exists():
            # Debug: list all files in temp_dir
            all_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    all_files.append(os.path.join(root, file))
            raise Exception(f"Output video not found. Searched paths: {possible_paths}. Files in temp_dir: {all_files}\n\nManim STDOUT:\n{stdout_str}\n\nManim STDERR:\n{stderr_str}")

        # Add subtitles if requested
        final_video_path = str(video_path)
        if include_subtitles and prompt:
            emit_progress("generating_subtitles", "Generating narration segments")
            logger.info(f"Subtitle generation requested: include_subtitles={include_subtitles}, prompt present={bool(prompt)}")
            logger.info(f"Original video path: {video_path}")
            from services.subtitle_generator import generate_and_add_subtitles
            try:
                logger.info("Starting subtitle generation...")
                # Create a wrapper callback to map subtitle progress to our progress callback
                def subtitle_progress_callback(stage: str, message: str):
                    # Map subtitle generator stages to render statuses
                    stage_mapping = {
                        "narration": "generating_subtitles",
                        "srt": "creating_srt",
                        "audio": "generating_audio",
                        "generating_audio": "generating_audio",
                        "ffmpeg": "stitching_subtitles"
                    }
                    mapped_stage = stage_mapping.get(stage, "generating_subtitles")
                    emit_progress(mapped_stage, message)

                final_video_path = await generate_and_add_subtitles(
                    video_path=str(video_path),
                    code=code,
                    prompt=prompt,
                    temp_dir=temp_dir,
                    model=model,
                    subtitle_style=subtitle_style,
                    font_size=subtitle_font_size,
                    enable_audio=enable_audio,
                    audio_language=audio_language,
                    audio_speaker_id=audio_speaker_id,
                    audio_speed=audio_speed,
                    progress_callback=subtitle_progress_callback,
                    session_id=session_id
                )
                logger.info(f"Subtitle generation completed! New video path: {final_video_path}")
                emit_progress("stitching_subtitles", "Subtitles added successfully")
            except Exception as e:
                # If subtitle generation fails, log but continue with original video
                logger.error(f"Subtitle generation failed: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                emit_progress("generating_subtitles", f"Subtitle generation failed: {str(e)}")
                # Return original video without subtitles
        else:
            logger.info(f"Subtitles NOT requested: include_subtitles={include_subtitles}, prompt present={bool(prompt)}")

        emit_progress("completed", "Video rendering completed successfully")
        return final_video_path, temp_dir

    except asyncio.CancelledError:
        # Handle cancellation gracefully
        logger.warning("Rendering task was cancelled")
        raise  # Re-raise to allow proper cleanup

    except Exception as e:
        # Clean up temp directory on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise e

    finally:
        # Ensure subprocess is terminated
        if process and process.returncode is None:
            try:
                logger.info("Terminating rendering subprocess...")
                process.terminate()
                try:
                    # Wait briefly for graceful termination
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if it doesn't terminate gracefully
                    logger.warning("Force killing rendering subprocess...")
                    process.kill()
                    await process.wait()
            except Exception as cleanup_error:
                logger.error(f"Error during subprocess cleanup: {cleanup_error}")
