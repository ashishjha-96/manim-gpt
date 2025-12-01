# Configuration Guide

## Environment Variables

The application uses environment variables for API keys and configuration. These can be set in a `.env` file or exported directly in your shell.

### API Keys

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your API key(s):

```bash
# For OpenAI
OPENAI_API_KEY=your-api-key

# For Anthropic (Claude)
ANTHROPIC_API_KEY=your-api-key

# For other providers, see LiteLLM documentation
```

Alternatively, set environment variables directly:

```bash
export OPENAI_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"
```

## Customizing Default Parameters

You can customize default parameters by modifying the Pydantic models in `main.py`:

### Video Generation Defaults

Edit the `VideoGenerationRequest` model to change:
- Default video format (mp4, webm, gif, mov)
- Default quality preset (low, medium, high, 4k)
- Default background color
- Default subtitle settings
- Default audio narration settings

### Code Generation Defaults

Edit the `CodeGenerationRequest` model to change:
- Default LLM model
- Default temperature
- Default max tokens

### Quality Presets

Modify the `QUALITY_PRESETS` dictionary to add or change quality settings:

```python
QUALITY_PRESETS = {
    "low": {"resolution": "480p15", "quality": "low_quality"},
    "medium": {"resolution": "720p30", "quality": "medium_quality"},
    "high": {"resolution": "1080p60", "quality": "high_quality"},
    "4k": {"resolution": "2160p60", "quality": "production_quality"},
    # Add your custom preset here
}
```

## LLM Model Configuration

### Supported Providers

The application uses LiteLLM, which supports 100+ models from various providers:

- **OpenAI**: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`
- **Anthropic**: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`
- **Cerebras**: `cerebras/zai-glm-4.6` (fast and free - default)
- **Cohere**: `command-nightly`
- **Google**: `gemini/gemini-pro`

See [LiteLLM documentation](https://docs.litellm.ai/docs/providers) for the full list.

### Changing the Default Model

To change the default model, edit the `model` field in the request models:

```python
model: str = Field(default="cerebras/zai-glm-4.6", description="LLM model to use")
```

### Model-Specific Configuration

Some models may require additional environment variables. Refer to the [LiteLLM provider documentation](https://docs.litellm.ai/docs/providers) for specific requirements.

## Video Rendering Configuration

### Output Formats

Supported formats:
- **MP4** (`.mp4`) - Most compatible, recommended for web
- **WebM** (`.webm`) - Open format, good for web
- **GIF** (`.gif`) - Animated images, smaller file size
- **MOV** (`.mov`) - QuickTime format, good for Apple ecosystem

### Quality Settings

| Quality | Resolution | Frame Rate | Use Case |
|---------|-----------|------------|----------|
| `low` | 480p | 15 fps | Quick previews, testing |
| `medium` | 720p | 30 fps | Standard quality (default) |
| `high` | 1080p | 60 fps | High-quality productions |
| `4k` | 2160p | 60 fps | Professional 4K content |

### Background Color

Background color can be specified as:
- Hex color: `#000000`, `#1a1a1a`
- Manim color name: `BLACK`, `WHITE`, `BLUE`, etc.

## Subtitle Configuration

### Enabling Subtitles

Set `include_subtitles: true` in the video generation request.

### Custom Subtitle Styles

You can customize subtitle appearance using ASS format styles:

```json
{
  "include_subtitles": true,
  "subtitle_style": "Fontname=Arial,Fontsize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000"
}
```

## Audio Narration Configuration

### Enabling Audio Narration

Set `enable_audio: true` in the video generation request.

### Audio Settings

- **Language**: `EN`, `ES`, `FR`, `ZH`, `JP`, `KR`
- **Speaker ID**: 0-10 (different voice options)
- **Speed**: 0.5-2.0 (speed multiplier)

Example:
```json
{
  "enable_audio": true,
  "audio_language": "EN",
  "audio_speaker_id": 0,
  "audio_speed": 1.0
}
```

See [TTS_INSTALLATION.md](../TTS_INSTALLATION.md) for detailed Piper TTS configuration.

## Project Structure

```
manim-gpt/
├── main.py                      # FastAPI application
├── frontend/                    # React + Tailwind UI
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── services/           # API client
│   │   ├── App.jsx             # Main app component
│   │   └── index.css           # Tailwind styles
│   └── package.json            # Frontend dependencies
├── api/                         # API route modules
│   ├── code_routes.py          # Code generation endpoints
│   ├── video_routes.py         # Video generation endpoints
│   ├── session_routes.py       # Session management
│   └── model_routes.py         # Model listing endpoints
├── models/                      # Data models and schemas
│   ├── schemas.py              # Pydantic request/response models
│   └── session.py              # Session state models
├── services/                    # Core business logic
│   ├── code_generation.py      # LLM code generation
│   ├── code_validator.py       # Code validation
│   ├── iterative_workflow.py   # LangGraph workflow
│   ├── session_manager.py      # Session management
│   └── video_rendering.py      # Video rendering
├── docs/                        # Documentation
│   ├── INSTALLATION.md
│   ├── API_DOCUMENTATION.md
│   ├── UI_GUIDE.md
│   ├── CONFIGURATION.md
│   └── TROUBLESHOOTING.md
├── pyproject.toml              # Project dependencies
├── .env                        # Environment variables (API keys)
├── .env.example                # Example environment file
└── README.md                   # Main documentation
```
