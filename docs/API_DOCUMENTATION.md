# API Documentation

## Overview

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API Endpoints

### POST /generate-video

Generate a complete Manim video from a text prompt.

**Request Body:**
```json
{
  "prompt": "Create an animation showing the Pythagorean theorem with a right triangle",
  "format": "mp4",
  "quality": "medium",
  "model": "cerebras/zai-glm-4.6",
  "max_tokens": 2000,
  "temperature": 0.7,
  "background_color": "#000000"
}
```

**Parameters:**
- `prompt` (required): Description of the Manim animation to generate
- `format` (optional): Output format - `mp4`, `webm`, `gif`, or `mov` (default: `mp4`)
- `quality` (optional): Video quality - `low`, `medium`, `high`, or `4k` (default: `medium`)
- `model` (optional): LLM model to use (default: `cerebras/zai-glm-4.6`)
- `max_tokens` (optional): Maximum tokens for code generation (default: 2000)
- `temperature` (optional): Temperature for code generation (default: 0.7)
- `background_color` (optional): Background color in hex or Manim color name
- `include_subtitles` (optional): Generate and add narration subtitles to the video (default: `false`)
- `subtitle_style` (optional): Custom subtitle style in ASS format (default: white text with black outline)

**Response:**
```json
{
  "video_path": "/tmp/manim_xyz/media/videos/scene/720p30/output.mp4",
  "generated_code": "from manim import *\n\nclass GeneratedScene(Scene):\n    ...",
  "model_used": "cerebras/zai-glm-4.6",
  "format": "mp4",
  "message": "Video generated successfully! Use /download-video endpoint to retrieve it."
}
```

### GET /download-video

Download a generated video file.

**Query Parameters:**
- `video_path` (required): Path to the video file (from generate-video response)

**Response:**
- Returns the video file with appropriate content-type header

### POST /generate-manim-code

Generate only Manim code without rendering the video.

**Request Body:**
```json
{
  "prompt": "Create an animation of a bouncing ball with physics",
  "model": "cerebras/zai-glm-4.6",
  "max_tokens": 1000,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "generated_code": "from manim import *\n\nclass GeneratedScene(Scene):\n    ...",
  "model_used": "cerebras/zai-glm-4.6"
}
```

### POST /generate-code

Generate generic Python code (non-Manim specific).

**Request Body:**
```json
{
  "prompt": "Create a function to calculate fibonacci numbers",
  "model": "cerebras/zai-glm-4.6",
  "max_tokens": 1000,
  "temperature": 0.7
}
```

### GET /models/providers

List all available LLM providers.

### GET /models/providers/{provider}

List all models for a specific provider (e.g., `/models/providers/openai`).

### GET /

Root endpoint - returns API status and available endpoints.

### GET /health

Health check endpoint.

## API Usage Examples

### Generate a Manim Video

#### Using curl

```bash
# Generate video
curl -X POST "http://localhost:8000/generate-video" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create an animation showing the derivative of x squared",
    "format": "mp4",
    "quality": "high"
  }'

# Download the video (use video_path from previous response)
curl "http://localhost:8000/download-video?video_path=/tmp/manim_xyz/media/videos/scene/1080p60/output.mp4" \
  --output animation.mp4
```

#### Using Python requests

```python
import requests

# Generate video
response = requests.post(
    "http://localhost:8000/generate-video",
    json={
        "prompt": "Create an animation of a sine wave transforming into a cosine wave",
        "format": "mp4",
        "quality": "medium",
        "background_color": "#1a1a1a"
    }
)

result = response.json()
print(f"Generated code:\n{result['generated_code']}")
print(f"Video path: {result['video_path']}")

# Download the video
video_response = requests.get(
    "http://localhost:8000/download-video",
    params={"video_path": result['video_path']}
)

with open("animation.mp4", "wb") as f:
    f.write(video_response.content)
```

### Generate Video with Audio Narration

Generate videos with synchronized text-to-speech audio narration:

```bash
# Using curl
curl -X POST "http://localhost:8000/video/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain the Pythagorean theorem with a visual proof",
    "format": "mp4",
    "quality": "high",
    "include_subtitles": true,
    "enable_audio": true,
    "audio_language": "EN",
    "audio_speaker_id": 0,
    "audio_speed": 1.0
  }'
```

```python
# Using Python
import requests

response = requests.post(
    "http://localhost:8000/video/generate",
    json={
        "prompt": "Show the quadratic formula with step-by-step derivation",
        "include_subtitles": True,    # Enable subtitles
        "enable_audio": True,          # Enable TTS audio
        "audio_language": "EN",        # Language: EN, ES, FR, ZH, JP, KR
        "audio_speaker_id": 0,         # Speaker voice (0-10)
        "audio_speed": 1.0             # Speed multiplier (0.5-2.0)
    }
)

# The generated video will have:
# 1. Visual animation
# 2. Subtitle text explaining what's happening
# 3. Synchronized audio narration speaking the subtitle text

print("Video saved as animation.mp4")
```

### Generate Manim Code Only

```python
import requests

response = requests.post(
    "http://localhost:8000/generate-manim-code",
    json={
        "prompt": "Create an animation showing quicksort algorithm",
        "temperature": 0.5
    }
)

print(response.json()["generated_code"])
```

## Supported Models

LiteLLM supports 100+ models. Some examples:
- **OpenAI**: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`
- **Anthropic**: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`
- **Cerebras**: `cerebras/zai-glm-4.6` (fast and free - default)
- **Cohere**: `command-nightly`
- **Google**: `gemini/gemini-pro`

See [LiteLLM documentation](https://docs.litellm.ai/docs/providers) for the full list.

## Video Quality Presets

| Quality | Resolution | Frame Rate | Use Case |
|---------|-----------|------------|----------|
| `low` | 480p | 15 fps | Quick previews, testing |
| `medium` | 720p | 30 fps | Standard quality (default) |
| `high` | 1080p | 60 fps | High-quality productions |
| `4k` | 2160p | 60 fps | Professional 4K content |

## Supported Output Formats

- **MP4** (`.mp4`) - Most compatible, recommended for web
- **WebM** (`.webm`) - Open format, good for web
- **GIF** (`.gif`) - Animated images, smaller file size
- **MOV** (`.mov`) - QuickTime format, good for Apple ecosystem
