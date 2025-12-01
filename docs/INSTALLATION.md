# Installation Guide

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

# 5. Start the React UI (Terminal 2)
cd frontend && npm install && npm run dev

# 6. Open http://localhost:5173 in your browser
```

**Using Google IDX**: Just open the project - everything auto-starts!

## Installation Methods

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

4. **Install Python dependencies** (includes Piper TTS for audio narration):
   ```bash
   uv sync
   ```

   This will automatically install:
   - All core dependencies
   - Piper TTS for high-quality TTS audio narration
   - All required audio processing libraries

   See [TTS_INSTALLATION.md](../TTS_INSTALLATION.md) for detailed Piper TTS information.

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

# Terminal 2: Start the React UI
cd frontend
npm install
npm run dev
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

Simply open the project in IDX and start using it!

### Option 2: Manual Installation

```bash
# Install dependencies using uv
uv sync

# Or using pip
pip install -e .
```

**Note**: Manual installation requires you to install system dependencies separately (see [System Requirements](#system-requirements) below).

## System Requirements

- **Python**: 3.11 or higher
- **Manim**: Requires LaTeX for text rendering (optional, but recommended)
- **FFmpeg**: Required for video rendering and subtitle generation
- **Storage**: Temporary space for video generation (cleaned up automatically)

**Note**: FFmpeg is required for both video rendering and subtitle generation. If you enable subtitles without FFmpeg installed, you'll receive an error message with installation instructions.

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
