# Manim GPT - AI-Powered Video Generation API

A FastAPI-based service that generates animated Manim videos from text prompts using LLM-powered code generation with iterative refinement.

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Installation](#installation)
  - [Using Nix (Recommended)](#option-1-using-nix-recommended)
  - [Manual Installation](#option-2-manual-installation)
- [Environment Setup](#environment-setup)
- [Using the Gradio UI](#using-the-gradio-ui)
- [API Documentation](#api-documentation)
- [API Usage Examples](#api-usage-examples)
- [Supported Models](#supported-models)
- [System Requirements](#system-requirements)
- [Troubleshooting](#troubleshooting)

## Quick Start

**Using Nix (Easiest)**:
```bash
# 1. Enter Nix development shell
nix develop --impure -f .idx/dev.nix

# 2. Install Python dependencies
uv sync

# 3. Set up API keys
cp .env.example .env
# Edit .env and add your API keys (e.g., OPENAI_API_KEY)

# 4. Start the backend (Terminal 1)
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# 5. Start the UI (Terminal 2, in Nix shell)
uv run gradio_app.py

# 6. Open http://localhost:7860 in your browser
```

**Using Google IDX**: Just open the project - everything auto-starts!

## Features

- **AI-Powered Code Generation**: Generate Manim animation code from natural language prompts
- **Iterative Code Refinement**: Automatic error detection and correction with LangGraph workflow
- **Real-time Streaming Updates**: Watch the generation process with live iteration logs
- **Manual Code Editing**: Fix errors yourself with built-in validation support
- **Session-based Workflow**: Maintain state across generation, editing, and rendering
- **Multi-Format Support**: Export videos in MP4, WebM, GIF, and MOV formats
- **Quality Presets**: Choose from low (480p), medium (720p), high (1080p), or 4K resolution
- **Customizable Rendering**: Control background color, frame rate, and video quality
- **Multiple LLM Models**: Supports 100+ models through LiteLLM integration
- **Async API**: Non-blocking video generation for better performance
- **Modern Web UI**: Beautiful Gradio interface with real-time progress tracking
- **Clean API Design**: RESTful endpoints with comprehensive documentation

## Installation

### Option 1: Using Nix (Recommended)

The easiest way to get started is using Nix, which provides all system dependencies including FFmpeg, LaTeX, and graphics libraries.

#### Setting up the Nix Environment

1. **Install Nix** (if not already installed):
   ```bash
   curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
   ```

2. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd manim-gpt
   ```

3. **Enter the Nix development shell**:
   ```bash
   nix develop --impure -f .idx/dev.nix
   ```

   This will automatically install:
   - Python 3.14
   - UV package manager
   - FFmpeg for video rendering
   - LaTeX (TeX Live) for mathematical text rendering
   - Graphics libraries (Cairo, Pango, Fontconfig, Freetype)
   - All required development tools

4. **Install Python dependencies**:
   ```bash
   uv sync
   ```

5. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

#### Running in Nix Environment

Once in the Nix shell, you can run both the API and UI:

```bash
# Terminal 1: Start the FastAPI backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start the Gradio UI (in a new terminal, also in Nix shell)
nix develop --impure -f .idx/dev.nix
uv run gradio_app.py
```

The Nix environment automatically:
- Sets up all required build flags for Cairo and graphics libraries
- Configures LaTeX packages needed for Manim
- Ensures consistent dependencies across different systems

#### Google IDX (Project IDX) Setup

This project is pre-configured for Google IDX. When you open this project in IDX:
1. The Nix environment will automatically initialize with Node.js and Python
2. Python dependencies will be installed automatically (uv sync)
3. React frontend dependencies will be installed automatically (npm install)
4. The FastAPI backend will auto-start on port 8000
5. The React + Tailwind UI will be available in the default web preview
6. The Gradio UI is also available as an alternative preview

Simply open the project in IDX and start using it! The React frontend will be the default preview.

### Option 2: Manual Installation

```bash
# Install dependencies using uv
uv sync

# Or using pip
pip install -e .
```

**Note**: Manual installation requires you to install system dependencies separately (see [System Requirements](#system-requirements) below).

## Environment Setup

### API Keys Configuration

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

Alternatively, you can set environment variables directly in your shell:

```bash
export OPENAI_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"
```

## User Interfaces

Manim GPT now offers **two modern web interfaces**:

### 1. React + Tailwind UI (New!)

A modern, responsive React application with a beautiful Tailwind CSS design.

**Features**:
- Real-time streaming code generation with live progress updates
- Interactive code editor with syntax highlighting
- LLM model selection from 100+ providers
- Video rendering with multiple formats and qualities
- Iteration tracking and detailed generation history
- Clean, professional design with excellent UX

**Starting the React UI**:
```bash
# Terminal 1: Start the FastAPI backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start the React frontend
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173` in your browser.

See [frontend/README.md](frontend/README.md) for detailed documentation.

### 2. Gradio UI (Classic)

The original Gradio interface provides an easy-to-use web interface for generating Manim videos with an iterative refinement workflow.

**Starting the Gradio UI**:

**If using Nix** (recommended):
```bash
# Terminal 1: Enter Nix shell and start the API
nix develop --impure -f .idx/dev.nix
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# Terminal 2: Enter Nix shell and start the Gradio UI
nix develop --impure -f .idx/dev.nix
uv run gradio_app.py
```

**If using manual installation**:
```bash
# Terminal 1: Start the API
uv run main.py

# Terminal 2: Start the Gradio UI
uv run gradio_app.py
```

Then open `http://localhost:7860` in your browser.

### Workflow

1. **Enter a prompt** describing your animation (e.g., "Create an animation showing the Pythagorean theorem")
2. **Configure settings**: Choose your LLM model, temperature, and max iterations
3. **Click "🚀 Generate with Streaming"** to start the iterative workflow
4. **Watch real-time progress** and iteration logs as the code is generated and refined
5. **Review and edit** the generated code if needed
6. **Click "🎬 Render Video"** once you have valid code to create your animation

### UI Features

- **Iterative Code Refinement**: Automatic error detection and fixing with up to 10 iterations
- **Real-time Streaming**: Watch each iteration's progress, errors, and fixes in real-time
- **Manual Code Editing**: Edit code directly in the UI and validate before rendering
- **Session Management**: Maintain state across generation, editing, and rendering
- **Multiple Output Formats**: MP4, WebM, GIF, or MOV
- **Quality Presets**: Low (480p), medium (720p), high (1080p), or 4K resolution
- **API Health Monitoring**: Check backend status at any time
- **Example Prompts**: Quick-start templates for common animations
- **Advanced Settings**: Full control over LLM model, temperature, and token limits

### Example Prompts

Try these prompts to get started:
- "Create an animation showing the Pythagorean theorem with a right triangle"
- "Animate a sine wave transforming into a cosine wave"
- "Show a bouncing ball with physics"
- "Visualize the area under a curve using Riemann sums"
- "Show matrix multiplication step by step"
- "Animate bubble sort with an array of numbers"

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
├── gradio_app.py        # Gradio web UI (classic)
├── frontend/            # React + Tailwind UI (new!)
│   ├── src/
│   │   ├── components/  # React components
│   │   ├── services/    # API client
│   │   ├── App.jsx      # Main app component
│   │   └── index.css    # Tailwind styles
│   ├── package.json
│   └── README.md        # Frontend documentation
├── api/                 # API route modules
│   ├── code_routes.py   # Code generation endpoints
│   ├── video_routes.py  # Video generation endpoints
│   ├── session_routes.py # Session management endpoints
│   └── model_routes.py  # Model listing endpoints
├── models/              # Data models and schemas
│   ├── schemas.py       # Pydantic request/response models
│   └── session.py       # Session state models
├── services/            # Core business logic
│   ├── code_generation.py      # LLM code generation
│   ├── code_validator.py       # Code validation
│   ├── iterative_workflow.py   # LangGraph workflow
│   ├── session_manager.py      # Session management
│   └── video_rendering.py      # Video rendering
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
