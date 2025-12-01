# Manim GPT

**AI-Powered Manim Video Generation** - Transform text prompts into stunning mathematical animations using LLM-powered code generation.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Manim](https://img.shields.io/badge/Manim-Community-orange.svg)](https://www.manim.community/)

## Quick Start

```bash
# Using Nix (Easiest)
nix develop --impure -f .idx/dev.nix
uv sync
cp .env.example .env  # Add your API keys

# Start the backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000

# Start the React UI (new terminal)
cd frontend && npm install && npm run dev  # React UI at http://localhost:5173
```

**Using Google IDX?** Just open the project - everything auto-starts!

## Features

✨ **AI-Powered Generation** - Natural language to Manim animations with iterative refinement
🎬 **Modern React UI** - Beautiful Tailwind CSS interface with real-time updates
🗣️ **Audio Narration** - Synchronized TTS narration with educational subtitles (Piper TTS)
🔄 **Smart Workflow** - LangGraph-powered automatic error detection and correction
📹 **Multi-Format Export** - MP4, WebM, GIF, MOV with quality presets (480p to 4K)
🤖 **100+ LLM Models** - OpenAI, Anthropic, Cerebras, Google, and more via LiteLLM
⚡ **Real-time Streaming** - Watch code generation and refinement live
🎨 **Customizable** - Background colors, frame rates, subtitle styles

## Documentation

📚 **Comprehensive guides available in the [`docs/`](docs/) directory:**

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions (Nix, manual, Google IDX)
- **[User Interface Guide](docs/UI_GUIDE.md)** - React UI and Gradio UI documentation
- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API reference and examples
- **[Configuration Guide](docs/CONFIGURATION.md)** - Customize settings, models, and rendering
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Example Prompts

```text
"Create an animation showing the Pythagorean theorem with a right triangle"
"Animate a sine wave transforming into a cosine wave"
"Visualize the area under a curve using Riemann sums"
"Show matrix multiplication step by step"
"Animate bubble sort with an array of numbers"
```

## Project Structure

```
manim-gpt/
├── main.py                      # FastAPI application
├── frontend/                    # React + Tailwind UI
│   ├── src/components/         # UI components
│   └── src/services/           # API client
├── api/                         # API routes
│   ├── code_routes.py          # Code generation
│   ├── video_routes.py         # Video generation
│   └── session_routes.py       # Session management
├── services/                    # Core logic
│   ├── code_generation.py      # LLM integration
│   ├── iterative_workflow.py   # LangGraph workflow
│   └── video_rendering.py      # Manim rendering
├── models/                      # Pydantic schemas
└── docs/                        # Documentation
```

## Built With

This project leverages these amazing open-source technologies:

- **[Manim Community](https://www.manim.community/)** - Mathematical animation engine
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework
- **[LiteLLM](https://github.com/BerriAI/litellm)** - Unified LLM API (100+ models)
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** - Iterative workflow orchestration
- **[React](https://react.dev/)** + **[Tailwind CSS](https://tailwindcss.com/)** - Modern UI framework
- **[Piper TTS](https://github.com/rhasspy/piper)** - Fast, local text-to-speech
- **[FFmpeg](https://ffmpeg.org/)** - Video processing and encoding
- **[UV](https://github.com/astral-sh/uv)** - Fast Python package manager

## Contributing

Contributions are welcome! Areas for improvement:
- New features and UI enhancements
- Better prompt engineering for code generation
- Additional quality presets and export formats
- Enhanced error handling and recovery
- Documentation improvements

## License

MIT License - see [LICENSE](LICENSE) for details.
