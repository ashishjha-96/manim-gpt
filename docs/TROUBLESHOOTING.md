# Troubleshooting Guide

## Common Issues and Solutions

### Video generation fails with "Manim rendering failed"

**Symptoms:**
- Error message indicates Manim rendering failed
- No video file is generated

**Solutions:**

1. **Verify Manim is installed:**
   ```bash
   uv pip list | grep manim
   ```

2. **Test Manim directly:**
   ```bash
   manim --version
   ```

3. **Check the generated code:**
   - Review the error traceback in the response
   - Look for syntax errors in the generated Python code
   - Common issues: missing imports, incorrect class names, invalid Manim syntax

4. **Reinstall dependencies:**
   ```bash
   uv sync
   # or
   pip install -e .
   ```

### "Command not found: manim"

**Symptoms:**
- Shell cannot find the `manim` command
- Error when trying to run Manim

**Solutions:**

1. **Install or reinstall dependencies:**
   ```bash
   uv sync
   # or
   pip install -e .
   ```

2. **Ensure you're in the correct Python environment:**
   - If using Nix, make sure you're in the Nix shell: `nix develop --impure -f .idx/dev.nix`
   - If using a virtual environment, ensure it's activated

3. **Check Python path:**
   ```bash
   which python
   python -m manim --version
   ```

### LaTeX errors

**Symptoms:**
- Errors mentioning LaTeX, TeX, or mathematical rendering
- Failures when using `Tex()` or `MathTex()` in animations

**Solutions:**

1. **If you don't need LaTeX text rendering:**
   - Avoid using `Tex()` or `MathTex()` in your prompts
   - Use `Text()` instead for simple text
   - Specify in your prompt: "Use Text() instead of MathTex()"

2. **If you need LaTeX support:**

   **macOS:**
   ```bash
   brew install --cask mactex
   ```

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get install texlive-full
   ```

   **Windows:**
   - Download and install [MiKTeX](https://miktex.org/download)

3. **Update LaTeX packages (if already installed):**
   ```bash
   # macOS/Linux
   sudo tlmgr update --all
   ```

### FFmpeg errors

**Symptoms:**
- Errors mentioning FFmpeg
- Video rendering fails at the final step
- Subtitle generation fails

**Solutions:**

1. **Install FFmpeg:**

   **macOS:**
   ```bash
   brew install ffmpeg
   ```

   **Ubuntu/Debian:**
   ```bash
   sudo apt-get update
   sudo apt-get install ffmpeg
   ```

   **Windows:**
   - Download from [FFmpeg website](https://ffmpeg.org/download.html)
   - Add to system PATH

2. **Verify FFmpeg installation:**
   ```bash
   ffmpeg -version
   ```

### API key errors

**Symptoms:**
- "Authentication failed" or "Invalid API key" errors
- 401 Unauthorized responses

**Solutions:**

1. **Check your `.env` file:**
   ```bash
   cat .env
   ```

2. **Ensure the correct environment variable is set:**
   - OpenAI: `OPENAI_API_KEY`
   - Anthropic: `ANTHROPIC_API_KEY`
   - Other providers: See [LiteLLM documentation](https://docs.litellm.ai/docs/providers)

3. **Verify API key is valid:**
   - Check the provider's dashboard
   - Ensure the key has the necessary permissions

4. **Restart the server after updating `.env`:**
   ```bash
   # Stop the server (Ctrl+C)
   # Start again
   uv run uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Port already in use

**Symptoms:**
- "Address already in use" error
- Cannot start the server on port 8000 or 7860

**Solutions:**

1. **Find and kill the process using the port:**

   **macOS/Linux:**
   ```bash
   # Find process on port 8000
   lsof -ti:8000 | xargs kill -9

   # Or for port 7860
   lsof -ti:7860 | xargs kill -9
   ```

   **Windows:**
   ```cmd
   # Find process
   netstat -ano | findstr :8000
   # Kill process (replace PID with actual process ID)
   taskkill /PID <PID> /F
   ```

2. **Use a different port:**
   ```bash
   # Backend
   uvicorn main:app --host 0.0.0.0 --port 8001

   # Gradio UI
   gradio gradio_app.py --server-port 7861
   ```

### Memory errors during video generation

**Symptoms:**
- "Out of memory" errors
- Process killed during rendering
- Slow or hanging generation

**Solutions:**

1. **Use lower quality settings:**
   - Change quality from `4k` to `high`, `medium`, or `low`
   - Lower resolution requires less memory

2. **Reduce max_tokens for code generation:**
   - Default is 2000, try 1000 or 1500
   - Simpler code uses less memory to render

3. **Close other applications:**
   - Free up system memory
   - Especially important for 4K rendering

4. **Simplify the prompt:**
   - Request simpler animations
   - Break complex animations into multiple parts

### Code validation fails

**Symptoms:**
- "Code validation failed" errors
- Generated code doesn't pass validation

**Solutions:**

1. **Review the validation errors:**
   - Check the error message for specific issues
   - Common problems: missing Scene class, invalid imports

2. **Manually edit the code:**
   - Use the UI's code editor to fix issues
   - Validate before rendering

3. **Adjust temperature:**
   - Lower temperature (0.3-0.5) for more conservative code
   - Higher temperature (0.7-0.9) for more creative output

4. **Try a different model:**
   - Some models are better at generating valid Manim code
   - Recommended: `gpt-4`, `claude-3-sonnet-20240229`

### Subtitle generation fails

**Symptoms:**
- Video generates but subtitles are missing
- Subtitle-related errors

**Solutions:**

1. **Ensure FFmpeg is installed:**
   ```bash
   ffmpeg -version
   ```

2. **Check subtitle settings:**
   - Verify `include_subtitles: true` is set
   - Check subtitle_style format if using custom styles

3. **Check logs for specific errors:**
   - Look at server console output
   - Check for subtitle file generation errors

### Audio narration fails

**Symptoms:**
- Video generates but audio is missing
- Piper TTS errors

**Solutions:**

1. **Ensure Piper TTS is installed:**
   ```bash
   uv pip list | grep piper-tts
   ```

2. **Reinstall Piper TTS:**
   ```bash
   uv sync
   ```

3. **Check audio settings:**
   - Verify `enable_audio: true` is set
   - Ensure audio_language is valid (EN, ES, FR, ZH, JP, KR)
   - Check audio_speaker_id is in range (0-10)

4. **See detailed TTS documentation:**
   - Refer to [TTS_INSTALLATION.md](../TTS_INSTALLATION.md)

## Getting Help

If you're still experiencing issues:

1. **Check the logs:**
   - Server console output often contains detailed error messages
   - UI error messages may provide clues

2. **Review the documentation:**
   - [Installation Guide](INSTALLATION.md)
   - [API Documentation](API_DOCUMENTATION.md)
   - [Configuration Guide](CONFIGURATION.md)

3. **Search for similar issues:**
   - Check the project's issue tracker
   - Search for error messages online

4. **Report a bug:**
   - Create a detailed issue report
   - Include error messages, logs, and steps to reproduce
   - Specify your environment (OS, Python version, etc.)
