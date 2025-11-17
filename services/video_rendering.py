import asyncio
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

from utils.constants import QUALITY_PRESETS


async def render_manim_video(
    code: str,
    output_format: str,
    quality: str,
    background_color: Optional[str] = None
) -> tuple[str, str]:
    """
    Render a Manim video from the generated code.

    Returns:
        tuple: (video_path, temp_dir)
    """
    # Create temporary directory for the Manim project
    temp_dir = tempfile.mkdtemp(prefix="manim_")

    try:
        # Write the generated code to a Python file
        script_path = Path(temp_dir) / "scene.py"
        with open(script_path, "w") as f:
            f.write(code)

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

        # Add background color if specified
        if background_color:
            cmd.extend(["--background_color", background_color])

        # Run manim rendering
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=temp_dir
        )

        stdout, stderr = await process.communicate()

        # Decode output for debugging
        stdout_str = stdout.decode() if stdout else ""
        stderr_str = stderr.decode() if stderr else ""

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
            import os
            all_files = []
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    all_files.append(os.path.join(root, file))
            raise Exception(f"Output video not found. Searched paths: {possible_paths}. Files in temp_dir: {all_files}\n\nManim STDOUT:\n{stdout_str}\n\nManim STDERR:\n{stderr_str}")

        return str(video_path), temp_dir

    except Exception as e:
        # Clean up temp directory on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise e
