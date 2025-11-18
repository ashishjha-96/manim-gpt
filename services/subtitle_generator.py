import asyncio
import re
import shutil
from pathlib import Path
from typing import List, Optional, Tuple
from litellm import acompletion


def check_ffmpeg_available() -> bool:
    """Check if ffmpeg is available in the system."""
    return shutil.which("ffmpeg") is not None


async def generate_narration_from_code(
    code: str,
    prompt: str,
    model: str = "cerebras/zai-glm-4.6",
    max_tokens: int = 1000,
    temperature: float = 0.7
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
        print(f"Failed to parse LLM narration response: {e}")
        print(f"Response was: {narration_text}")
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
    subtitle_style: Optional[str] = None
) -> None:
    """
    Add subtitles to video using FFmpeg.

    Args:
        video_path: Path to input video
        srt_path: Path to SRT subtitle file
        output_path: Path for output video with subtitles
        subtitle_style: Optional custom subtitle style (ASS format)

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
        # ASS subtitle style parameters
        subtitle_style = (
            "FontName=DejaVu Sans,FontSize=24,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
            "Alignment=2,MarginV=30"
        )

    # Build FFmpeg command to burn subtitles into video
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

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        stderr_str = stderr.decode() if stderr else ""
        raise Exception(f"FFmpeg subtitle addition failed (code {process.returncode}):\n{stderr_str}")


async def generate_and_add_subtitles(
    video_path: str,
    code: str,
    prompt: str,
    temp_dir: str,
    model: str = "cerebras/zai-glm-4.6",
    subtitle_style: Optional[str] = None
) -> str:
    """
    Complete pipeline: generate narration, create SRT, add to video.

    Args:
        video_path: Path to original video
        code: Manim code that was used to generate the video
        prompt: User's original prompt
        temp_dir: Temporary directory for intermediate files
        model: LLM model to use for narration generation
        subtitle_style: Optional custom subtitle style

    Returns:
        Path to video with subtitles

    Raises:
        RuntimeError: If ffmpeg is not available
    """
    print(f"[Subtitle Generator] Starting subtitle generation pipeline")
    print(f"[Subtitle Generator] Video path: {video_path}")
    print(f"[Subtitle Generator] Model: {model}")
    print(f"[Subtitle Generator] Prompt: {prompt[:100]}...")

    # Check ffmpeg availability early
    if not check_ffmpeg_available():
        raise RuntimeError(
            "FFmpeg is not installed. Subtitle generation requires FFmpeg. "
            "Please install it from https://ffmpeg.org/download.html"
        )
    print(f"[Subtitle Generator] FFmpeg is available")
    temp_path = Path(temp_dir)

    # Generate narration segments
    print(f"[Subtitle Generator] Generating narration segments using LLM...")
    segments = await generate_narration_from_code(code, prompt, model=model)
    print(f"[Subtitle Generator] Generated {len(segments)} narration segments")

    # Create SRT file
    srt_path = temp_path / "subtitles.srt"
    print(f"[Subtitle Generator] Creating SRT file at: {srt_path}")
    create_srt_file(segments, str(srt_path))
    print(f"[Subtitle Generator] SRT file created successfully")

    # Add subtitles to video
    video_path_obj = Path(video_path)
    output_path = video_path_obj.parent / f"{video_path_obj.stem}_subtitled{video_path_obj.suffix}"
    print(f"[Subtitle Generator] Adding subtitles to video using FFmpeg...")
    print(f"[Subtitle Generator] Input video: {video_path}")
    print(f"[Subtitle Generator] Output video: {output_path}")

    await add_subtitles_to_video(
        video_path,
        str(srt_path),
        str(output_path),
        subtitle_style
    )

    print(f"[Subtitle Generator] Subtitles added successfully!")
    print(f"[Subtitle Generator] Final video with subtitles: {output_path}")
    return str(output_path)
