# Manim GPT - AI-Powered Video Generation API

A FastAPI-based service that generates animated Manim videos from text prompts using LLM-powered code generation.

## Features

- **AI-Powered Code Generation**: Generate Manim animation code from natural language prompts
- **Multi-Format Support**: Export videos in MP4, WebM, GIF, and MOV formats
- **Quality Presets**: Choose from low (480p), medium (720p), high (1080p), or 4K resolution
- **Customizable Rendering**: Control background color, frame rate, and video quality
- **Multiple LLM Models**: Supports 100+ models through LiteLLM integration
- **Async API**: Non-blocking video generation for better performance
- **Clean API Design**: RESTful endpoints with Pydantic models

## Installation

```bash
# Install dependencies using uv
uv sync

# Or using pip
pip install -e .
```

## Environment Setup

### Using .env file (Recommended)

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API key(s):
```bash
# For OpenAI
OPENAI_API_KEY=your-api-key

# For Anthropic (Claude)
ANTHROPIC_API_KEY=your-api-key

# For other providers, see LiteLLM documentation
```

The application will automatically load environment variables from the `.env` file.

### Using environment variables directly

Alternatively, you can set environment variables in your shell:

```bash
# For OpenAI
export OPENAI_API_KEY="your-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-api-key"

# For other providers, see LiteLLM documentation
```

## Running the Application

### Option 1: Gradio UI (Recommended for beginners)

The easiest way to use Manim GPT is through the Gradio web interface:

```bash
# First, start the FastAPI backend server in one terminal
uv run main.py

# Then, in another terminal, start the Gradio UI
uv run gradio_app.py
```

The Gradio UI will be available at `http://localhost:7860`

### Option 2: FastAPI Server (For API access)

```bash
# Run with Python
uv run main.py

# Or with uvicorn directly
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Documentation

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

## Using the Gradio UI

The Gradio UI provides an easy-to-use web interface for generating Manim videos:

1. **Start the servers**:
   ```bash
   # Terminal 1: Start the API
   uv run main.py

   # Terminal 2: Start the Gradio UI
   uv run gradio_app.py
   ```

2. **Open the UI**: Navigate to `http://localhost:7860` in your browser

3. **Generate videos**:
   - Enter a prompt describing your animation
   - Select format (MP4, WebM, GIF, or MOV)
   - Choose quality preset (low, medium, high, or 4k)
   - Click "Generate Video"
   - View the generated video and code

4. **Features**:
   - Video generation with preview
   - Code-only generation (faster)
   - Example prompts to get started
   - API health monitoring
   - Advanced settings (model selection, temperature, tokens)

## Example Usage

### Using Gradio UI

Simply enter prompts like:
- "Create an animation showing the Pythagorean theorem with a right triangle"
- "Animate a sine wave transforming into a cosine wave"
- "Show a bouncing ball with physics"

### Generate a Manim Video (API)

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

### Example Prompts

Here are some example prompts you can try:

- **Mathematics**: "Animate the proof of the Pythagorean theorem"
- **Physics**: "Show a pendulum swinging with decreasing amplitude"
- **Graphs**: "Create a bar chart that animates upward"
- **Geometry**: "Demonstrate how to construct a circle from its center"
- **Calculus**: "Visualize the area under a curve using Riemann sums"
- **Linear Algebra**: "Show matrix multiplication step by step"
- **Algorithms**: "Animate bubble sort with an array of numbers"

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

## Configuration

You can customize default parameters by modifying the Pydantic models in [main.py](main.py):
- `VideoGenerationRequest`: Default video generation settings
- `CodeGenerationRequest`: Default code generation settings
- `QUALITY_PRESETS`: Custom quality/resolution presets

## System Requirements

- **Python**: 3.11 or higher
- **Manim**: Requires LaTeX for text rendering (optional, but recommended)
- **FFmpeg**: Required for video rendering
- **Storage**: Temporary space for video generation (cleaned up automatically)

### Installing System Dependencies

#### macOS
```bash
brew install ffmpeg
brew install --cask mactex  # Optional, for LaTeX support
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install ffmpeg
sudo apt-get install texlive-full  # Optional, for LaTeX support
```

#### Windows
Download and install:
- [FFmpeg](https://ffmpeg.org/download.html)
- [MiKTeX](https://miktex.org/download) (optional, for LaTeX support)

## Troubleshooting

### Video generation fails with "Manim rendering failed"

1. Ensure Manim is installed: `uv pip list | grep manim`
2. Test Manim directly: `manim --version`
3. Check the generated code for syntax errors in the error traceback

### "Command not found: manim"

Install or reinstall dependencies:
```bash
uv sync
# or
pip install -e .
```

### LaTeX errors

If you get LaTeX-related errors and don't need LaTeX text rendering:
- Avoid using `Tex()` or `MathTex()` in prompts
- Use `Text()` instead for simple text
- Or install LaTeX (see System Requirements above)

## Project Structure

```
manim-gpt/
├── main.py              # FastAPI application entry point
├── gradio_app.py        # Gradio web UI
├── api/                 # API route modules
│   ├── code_routes.py   # Code generation endpoints
│   ├── video_routes.py  # Video generation endpoints
│   └── model_routes.py  # Model listing endpoints
├── pyproject.toml       # Project dependencies
├── .env                 # Environment variables (API keys)
├── .env.example         # Example environment file
└── README.md           # This file
```

## Contributing

Contributions are welcome! Feel free to:
- Add new features
- Improve video generation prompts
- Add more quality presets
- Enhance error handling
- Improve documentation

## License

This project is open source and available under the MIT License.
