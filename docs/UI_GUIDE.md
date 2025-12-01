# User Interface Guide

## React + Tailwind UI

Manim GPT features a modern, responsive React application with a beautiful Tailwind CSS design.

### Features

- **Real-time Streaming** - Watch code generation and refinement with live progress updates
- **Interactive Code Editor** - Built-in syntax highlighting for editing generated code
- **Smart Model Selection** - Choose from 100+ LLM providers and models
- **Flexible Rendering** - Multiple video formats (MP4, WebM, GIF, MOV) and quality presets
- **Iteration Tracking** - Detailed generation history with error logs and fixes
- **Session Management** - Maintain state across generation, editing, and rendering
- **Audio Narration** - AI-generated educational subtitles with TTS narration
- **Modern Design** - Clean, professional UI with excellent user experience

### Getting Started

#### Start the Backend

```bash
# Terminal 1: FastAPI backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Start the React UI

```bash
# Terminal 2: React frontend
cd frontend
npm install
npm run dev
```

Then open `http://localhost:5173` in your browser.

See [frontend/README.md](../frontend/README.md) for detailed React documentation.

### Workflow

1. **Enter a Prompt**
   - Describe your desired animation in natural language
   - Example: "Create an animation showing the Pythagorean theorem with a right triangle"

2. **Configure Settings**
   - Select your LLM model (OpenAI, Anthropic, Cerebras, etc.)
   - Adjust temperature (0.1-1.0) for creativity vs. precision
   - Set max iterations for error correction (1-10)

3. **Generate Code**
   - Click "Generate" to start the iterative workflow
   - Watch real-time progress as code is generated and refined
   - View iteration logs showing errors and fixes

4. **Review & Edit**
   - Inspect the generated Manim code
   - Make manual edits if needed
   - Validate code before rendering

5. **Render Video**
   - Choose output format (MP4, WebM, GIF, MOV)
   - Select quality preset (480p, 720p, 1080p, 4K)
   - Enable subtitles and audio narration if desired
   - Download the final video

### UI Components

#### Generation Form
- Prompt input with example suggestions
- Model selection dropdown (100+ models)
- Advanced settings (temperature, max tokens, iterations)
- Real-time API health status

#### Code Editor
- Syntax-highlighted Manim code
- Line numbers and proper indentation
- Manual editing capabilities
- Code validation before rendering

#### Iteration Logs
- Real-time streaming updates
- Error messages with stack traces
- Fix attempts and solutions
- Success indicators

#### Video Player
- Preview rendered animations
- Download button for final video
- Format and quality information

### Example Prompts

```text
"Create an animation showing the Pythagorean theorem with a right triangle"
"Animate a sine wave transforming into a cosine wave"
"Show a bouncing ball with physics"
"Visualize the area under a curve using Riemann sums"
"Show matrix multiplication step by step"
"Animate bubble sort with an array of numbers"
"Explain the derivative of x squared visually"
"Create a rotating 3D cube with colored faces"
```

### Keyboard Shortcuts

- **Ctrl/Cmd + Enter** - Submit generation form
- **Ctrl/Cmd + S** - Save code changes (when editing)
- **Esc** - Clear current prompt

### Tips for Best Results

1. **Be Specific** - Detailed prompts produce better animations
2. **Start Simple** - Test basic concepts before complex animations
3. **Use Lower Temperature** - For mathematical accuracy (0.3-0.5)
4. **Enable Iterations** - Allow 3-5 iterations for error correction
5. **Preview First** - Use low quality for quick testing
6. **Add Narration** - Enable subtitles for educational content
