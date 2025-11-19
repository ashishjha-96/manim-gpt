"""
Audio generation service using Piper TTS (offline neural text-to-speech).

This service provides high-quality, offline text-to-speech audio generation
for educational narration in manim-gpt videos.

Features:
- Neural voice quality (ONNX-optimized)
- Multi-language support (EN, ES, FR, ZH, JP, KR)
- Works completely offline
- Lightweight models (5-50MB per voice)
- Fast inference
- Adjustable speech speed (0.5x - 2.0x)
- Automatic duration synchronization with subtitles
"""

import asyncio
import os
import wave
from pathlib import Path
from typing import List, Dict, Optional, Callable
from pydub import AudioSegment

from utils.logger import get_logger, get_logger_with_session

# Voice model paths - these will be downloaded to this directory
VOICE_MODELS_DIR = Path(__file__).parent.parent / "voice_models"

# Voice model mapping for Piper TTS
# Format: language -> (model_name, quality_level)
# Models will be downloaded from HuggingFace: rhasspy/piper-voices
PIPER_VOICE_MODELS = {
    "EN": [
        ("en_US-amy-medium", "medium"),           # Female (speaker_id=0)
        ("en_US-ryan-medium", "medium"),          # Male (speaker_id=1)
        ("en_GB-alan-medium", "medium")           # Male British (speaker_id=2)
    ],
    "ES": [
        ("es_ES-davefx-medium", "medium")         # Male Spanish (speaker_id=0)
    ],
    "FR": [
        ("fr_FR-siwis-medium", "medium")          # Female French (speaker_id=0)
    ],
    "ZH": [
        ("zh_CN-huayan-medium", "medium")         # Female Chinese (speaker_id=0)
    ],
    "JP": [
        ("ja_JP-shinji-medium", "medium")         # Male Japanese (speaker_id=0)
    ],
    "KR": [
        ("ko_KR-kss-medium", "medium")            # Female Korean (speaker_id=0)
    ]
}

# Cache for loaded Piper voice models
_voice_cache = {}


async def check_pipertts_available() -> bool:
    """
    Check if Piper TTS is available and can be imported.

    Returns:
        bool: True if Piper TTS is available, False otherwise
    """
    try:
        import piper
        logger.info("Piper TTS is available")
        return True
    except ImportError:
        logger.error("Piper TTS is not installed")
        logger.error("Install with: pip install piper-tts")
        return False


def get_available_speakers(language: str = "EN") -> Dict[int, str]:
    """
    Get available speaker voices for a given language.

    Args:
        language: Language code (EN, ES, FR, ZH, JP, KR)

    Returns:
        Dictionary mapping speaker IDs to voice descriptions
    """
    voice_descriptions = {
        "EN": {
            0: "Amy (Female, US)",
            1: "Ryan (Male, US)",
            2: "Alan (Male, UK)"
        },
        "ES": {0: "Davefx (Male, Spain)"},
        "FR": {0: "Siwis (Female, France)"},
        "ZH": {0: "Huayan (Female, China)"},
        "JP": {0: "Shinji (Male, Japan)"},
        "KR": {0: "KSS (Female, Korea)"}
    }

    return voice_descriptions.get(language, voice_descriptions["EN"])


def get_model_path(language: str = "EN", speaker_id: int = 0) -> tuple:
    """
    Get the model path for a given language and speaker.

    Args:
        language: Language code
        speaker_id: Speaker voice ID

    Returns:
        Tuple of (model_file_path, config_file_path)
    """
    models = PIPER_VOICE_MODELS.get(language, PIPER_VOICE_MODELS["EN"])
    model_name, quality = models[speaker_id % len(models)]

    model_file = VOICE_MODELS_DIR / f"{model_name}.onnx"
    config_file = VOICE_MODELS_DIR / f"{model_name}.onnx.json"

    return str(model_file), str(config_file)


async def download_voice_model(language: str = "EN", speaker_id: int = 0) -> tuple:
    """
    Download a Piper voice model from HuggingFace if not already present.

    Args:
        language: Language code
        speaker_id: Speaker voice ID

    Returns:
        Tuple of (model_path, config_path)
    """
    model_path, config_path = get_model_path(language, speaker_id)

    # Create models directory if it doesn't exist
    VOICE_MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Check if already downloaded
    if Path(model_path).exists() and Path(config_path).exists():
        logger.debug(f"Voice model already exists: {model_path}")
        return model_path, config_path

    # Download from HuggingFace
    models = PIPER_VOICE_MODELS.get(language, PIPER_VOICE_MODELS["EN"])
    model_name, quality = models[speaker_id % len(models)]

    # Parse model name: en_US-amy-medium -> en/en_US/amy/medium
    parts = model_name.split('-')
    if len(parts) >= 2:
        locale_parts = parts[0].split('_')  # en_US -> ['en', 'US']
        voice_name = parts[1]  # amy

        lang_code = locale_parts[0]  # en
        country_code = locale_parts[1] if len(locale_parts) > 1 else ""  # US

        # Construct proper path: en/en_US/amy/medium
        base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/{lang_code}/{parts[0]}/{voice_name}/{quality}"
    else:
        raise ValueError(f"Invalid model name format: {model_name}")

    logger.info(f"Downloading Piper voice model: {model_name}")

    try:
        import httpx

        async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
            # Download model file (.onnx)
            logger.info(f"Downloading {model_name}.onnx...")
            model_url = f"{base_url}/{model_name}.onnx"
            response = await client.get(model_url)
            response.raise_for_status()

            with open(model_path, 'wb') as f:
                f.write(response.content)

            # Download config file (.onnx.json)
            logger.info(f"Downloading {model_name}.onnx.json...")
            config_url = f"{base_url}/{model_name}.onnx.json"
            response = await client.get(config_url)
            response.raise_for_status()

            with open(config_path, 'wb') as f:
                f.write(response.content)

        logger.info(f"Voice model downloaded successfully: {model_name}")
        return model_path, config_path

    except Exception as e:
        logger.error(f"Failed to download voice model: {e}")
        raise RuntimeError(f"Voice model download failed: {e}")


def load_voice_model(model_path: str):
    """
    Load a Piper voice model (with caching).

    Args:
        model_path: Path to the ONNX model file

    Returns:
        Loaded Piper Voice object
    """
    if model_path in _voice_cache:
        return _voice_cache[model_path]

    try:
        from piper import PiperVoice

        logger.info(f"Loading Piper voice model: {model_path}")
        voice = PiperVoice.load(model_path)
        _voice_cache[model_path] = voice
        logger.info("Voice model loaded successfully")

        return voice

    except Exception as e:
        logger.error(f"Failed to load voice model: {e}")
        raise RuntimeError(f"Voice model loading failed: {e}")


async def generate_audio_chunk(
    text: str,
    output_path: str,
    speaker_id: int = 0,
    language: str = "EN",
    speed: float = 1.0
) -> str:
    """
    Generate audio for a single text chunk using Piper TTS.

    Args:
        text: Text to convert to speech
        output_path: Path where to save the audio file (WAV format)
        speaker_id: Speaker voice ID (0-2 for EN, 0 for others)
        language: Language code (EN, ES, FR, ZH, JP, KR)
        speed: Speech speed multiplier (0.5 - 2.0)

    Returns:
        Path to the generated audio file

    Raises:
        ImportError: If Piper TTS is not installed
        Exception: If audio generation fails
    """
    try:
        from piper import PiperVoice
    except ImportError:
        raise ImportError(
            "Piper TTS is not installed. Install with: pip install piper-tts"
        )

    logger.debug(f"Generating audio: language={language}, speaker={speaker_id}, speed={speed}x, text='{text[:50]}...'")

    # Get and download model if needed
    model_path, config_path = await download_voice_model(language, speaker_id)

    # Load voice model (cached)
    voice = load_voice_model(model_path)

    try:
        # Generate audio using Piper
        # Run in thread pool since Piper is synchronous
        loop = asyncio.get_event_loop()

        def _synthesize():
            # Piper TTS synthesize method returns AudioChunk objects
            # AudioChunk has audio_int16_bytes property with the raw audio
            with wave.open(output_path, 'wb') as wav_file:
                # Get the first chunk to read sample rate and config
                first_chunk = None
                for audio_chunk in voice.synthesize(text):
                    if first_chunk is None:
                        first_chunk = audio_chunk
                        # Configure WAV parameters from first chunk
                        wav_file.setnchannels(audio_chunk.sample_channels)
                        wav_file.setsampwidth(audio_chunk.sample_width)
                        wav_file.setframerate(audio_chunk.sample_rate)

                    # Write the audio bytes
                    wav_file.writeframes(audio_chunk.audio_int16_bytes)

        await loop.run_in_executor(None, _synthesize)

        logger.debug(f"WAV generated: {output_path}")

        # Adjust speed if needed
        if abs(speed - 1.0) > 0.05:  # Only adjust if significantly different from 1.0
            logger.debug(f"Adjusting speed to {speed}x")
            audio = AudioSegment.from_wav(output_path)

            if speed > 1.0:
                # Speed up
                audio = audio.speedup(playback_speed=speed)
            else:
                # Slow down by changing frame rate
                audio = audio._spawn(
                    audio.raw_data,
                    overrides={'frame_rate': int(audio.frame_rate * speed)}
                ).set_frame_rate(audio.frame_rate)

            audio.export(output_path, format='wav')

        return output_path

    except Exception as e:
        raise Exception(f"Audio generation failed for text '{text[:50]}...': {e}")


async def adjust_audio_duration(
    audio_path: str,
    target_duration: float,
    output_path: str = None
) -> str:
    """
    Adjust audio duration to match target duration by changing playback speed.

    Args:
        audio_path: Path to input audio file
        target_duration: Desired duration in seconds
        output_path: Path for output file (if None, overwrites input)

    Returns:
        Path to adjusted audio file
    """
    if output_path is None:
        output_path = audio_path

    # Load audio
    audio = AudioSegment.from_wav(audio_path)
    current_duration = len(audio) / 1000.0  # Convert ms to seconds

    # If durations are very close (within 100ms), don't adjust
    if abs(current_duration - target_duration) < 0.1:
        logger.debug(f"Duration close enough ({current_duration:.2f}s vs {target_duration:.2f}s), skipping adjustment")
        if output_path != audio_path:
            audio.export(output_path, format='wav')
        return output_path

    # Calculate speed adjustment needed
    speed_factor = current_duration / target_duration

    logger.debug(f"Adjusting audio: {current_duration:.2f}s → {target_duration:.2f}s (speed={speed_factor:.2f}x)")

    # Adjust speed
    if speed_factor > 1.0:
        # Speed up
        adjusted = audio.speedup(playback_speed=speed_factor)
    else:
        # Slow down by changing frame rate
        adjusted = audio._spawn(
            audio.raw_data,
            overrides={'frame_rate': int(audio.frame_rate * speed_factor)}
        ).set_frame_rate(audio.frame_rate)

    # Export adjusted audio
    adjusted.export(output_path, format='wav')

    return output_path


async def generate_audio_from_segments(
    segments: List[Dict],
    output_path: str,
    speaker_id: int = 0,
    language: str = "EN",
    base_speed: float = 1.0,
    progress_callback: Optional[Callable[[str, str], None]] = None,
    session_id: Optional[str] = None
) -> str:
    """
    Generate synchronized audio from narration segments.

    Each segment should have 'text' and 'duration' keys. The audio will be
    generated to match the specified durations and concatenated into a single file.

    Args:
        segments: List of narration segments with 'text' and 'duration'
        output_path: Path where to save the final audio file
        speaker_id: Speaker voice ID (0-2 for EN, 0 for others)
        language: Language code (EN, ES, FR, ZH, JP, KR)
        base_speed: Base speech speed multiplier (0.5 - 2.0)
        progress_callback: Optional callback(stage, message) for progress updates
        session_id: Optional session ID for logging context

    Returns:
        Path to the generated audio file

    Raises:
        ImportError: If Piper TTS is not installed
        Exception: If audio generation fails
    """
    # Create session-aware logger if session_id provided, otherwise use default logger
    logger = get_logger_with_session("AudioGenerator", session_id) if session_id else get_logger("AudioGenerator")

    def emit_progress(stage: str, message: str):
        """Helper to emit progress if callback is provided."""
        if progress_callback:
            progress_callback(stage, message)

    logger.info(f"Generating audio from {len(segments)} segments")
    logger.info(f"Language: {language}, Speaker: {speaker_id}, Base speed: {base_speed}x")

    # Create temp directory for intermediate files
    temp_dir = Path(output_path).parent / "audio_temp"
    temp_dir.mkdir(exist_ok=True)

    try:
        audio_segments = []

        # Generate audio for each segment
        for idx, segment in enumerate(segments, start=1):
            text = segment['text']
            target_duration = segment['duration']

            logger.info(f"Processing segment {idx}/{len(segments)}: '{text[:50]}...' ({target_duration}s)")
            emit_progress("generating_audio", f"Processing segment {idx}/{len(segments)}")

            # Generate audio chunk
            chunk_path = str(temp_dir / f"segment_{idx:03d}.wav")
            await generate_audio_chunk(
                text=text,
                output_path=chunk_path,
                speaker_id=speaker_id,
                language=language,
                speed=base_speed
            )

            # Adjust to match target duration
            adjusted_path = str(temp_dir / f"segment_{idx:03d}_adjusted.wav")
            await adjust_audio_duration(
                audio_path=chunk_path,
                target_duration=target_duration,
                output_path=adjusted_path
            )

            # Load adjusted segment
            audio_segment = AudioSegment.from_wav(adjusted_path)
            audio_segments.append(audio_segment)

            # Clean up intermediate files
            if os.path.exists(chunk_path):
                os.remove(chunk_path)

        # Concatenate all segments
        logger.info("Concatenating all audio segments")
        emit_progress("generating_audio", "Combining audio segments")

        final_audio = audio_segments[0]
        for segment in audio_segments[1:]:
            final_audio += segment

        # Export final audio
        final_audio.export(output_path, format='wav', parameters=["-ac", "2", "-ar", "44100"])

        total_duration = len(final_audio) / 1000.0
        logger.info(f"Audio generation complete: {output_path} ({total_duration:.2f}s)")

        # Clean up temp directory
        for file in temp_dir.glob("*.wav"):
            file.unlink()
        temp_dir.rmdir()

        return output_path

    except Exception as e:
        # Clean up on error
        logger.error(f"Audio generation failed: {e}")
        if temp_dir.exists():
            for file in temp_dir.glob("*.wav"):
                try:
                    file.unlink()
                except:
                    pass
            try:
                temp_dir.rmdir()
            except:
                pass
        raise


# Aliases for backward compatibility
check_edgetts_available = check_pipertts_available
check_melotts_available = check_pipertts_available
