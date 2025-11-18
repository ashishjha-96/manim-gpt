"""
Gradio UI for Manim GPT - AI-Powered Video Generation
"""
import gradio as gr
import httpx
import os
from pathlib import Path
import asyncio
import json
from typing import Optional, Tuple

# API base URL
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Default models
DEFAULT_MODEL = "cerebras/llama3.1-8b"
POPULAR_MODELS = [
    "cerebras/llama3.1-8b",
    "gpt-3.5-turbo",
    "gpt-4",
    "claude-3-sonnet-20240229",
    "gemini/gemini-pro",
]


async def fetch_providers() -> list:
    """Fetch available LLM providers from the API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_URL}/models/providers")
            if response.status_code == 200:
                data = response.json()
                return data.get("providers", [])
            return []
    except Exception as e:
        print(f"Error fetching providers: {e}")
        return []


async def fetch_models_by_provider(provider: str) -> list:
    """Fetch available models for a specific provider."""
    if not provider:
        return POPULAR_MODELS

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_URL}/models/providers/{provider}")
            if response.status_code == 200:
                data = response.json()
                return data.get("models", [])
            return []
    except Exception as e:
        print(f"Error fetching models for {provider}: {e}")
        return []


def get_providers() -> list:
    """Synchronous wrapper to get providers."""
    return asyncio.run(fetch_providers())


def get_models_by_provider(provider: str) -> gr.Dropdown:
    """Update model dropdown based on selected provider."""
    if provider == "Popular Models":
        return gr.Dropdown(choices=POPULAR_MODELS, value=DEFAULT_MODEL, allow_custom_value=True)

    models = asyncio.run(fetch_models_by_provider(provider))
    if not models:
        models = POPULAR_MODELS
    return gr.Dropdown(choices=models, value=models[0] if models else DEFAULT_MODEL, allow_custom_value=True)


async def iterative_generate_streaming(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    max_iterations: int,
    progress=gr.Progress()
) -> Tuple[str, str, str, str, str]:
    """
    Generate Manim code with iterative refinement using streaming session API.
    This function calls the /session/generate-stream endpoint which streams
    real-time progress updates for each iteration.
    """
    if not prompt:
        return "❌ **Error:** Please enter a prompt", "", "", "", ""

    progress(0.0, desc="🚀 Starting session...")

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # Start iterative generation session with streaming
            progress(0.1, desc="📝 Creating session and running workflow...")

            iteration_log = "# Iteration Log\n\n"
            session_id = ""
            final_code = ""
            final_validation = {}
            final_status = ""
            current_iter = 0

            async with client.stream(
                "POST",
                f"{API_URL}/session/generate-stream",
                json={
                    "prompt": prompt,
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "max_iterations": max_iterations,
                },
                timeout=600.0
            ) as response:
                if response.status_code != 200:
                    error_detail = await response.aread()
                    error_msg = f"❌ **API Error ({response.status_code}):**\n\n{error_detail.decode()}"
                    return error_msg, "", "", "", ""

                # Process SSE events
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        try:
                            data = json.loads(data_str)
                            event_type = data.get("event", "unknown")

                            if event_type == "start":
                                session_id = data.get("session_id", "")
                                iteration_log += f"**Session Started:** `{session_id}`\n\n"
                                iteration_log += f"**Max Iterations:** {data.get('max_iterations', 0)}\n\n"
                                iteration_log += "---\n\n"

                            elif event_type == "progress":
                                node = data.get("node", "")
                                current_iter = data.get("current_iteration", 0)
                                status = data.get("status", "")
                                iterations_history = data.get("iterations_history", [])

                                # Update progress bar
                                progress_pct = current_iter / max_iterations
                                progress(progress_pct, desc=f"🔄 Iteration {current_iter}/{max_iterations} - {status}")

                                # Log iteration details
                                if iterations_history and len(iterations_history) >= current_iter:
                                    latest_iter = iterations_history[-1]
                                    iteration_log += f"## Iteration {latest_iter['iteration_number']}\n\n"
                                    iteration_log += f"**Node:** `{node}`\n\n"
                                    iteration_log += f"**Status:** {latest_iter['status']}\n\n"

                                    # Show code snippet
                                    code_snippet = latest_iter.get('generated_code', '')
                                    if code_snippet:
                                        preview = code_snippet[:200] + "..." if len(code_snippet) > 200 else code_snippet
                                        iteration_log += f"**Generated Code Preview:**\n```python\n{preview}\n```\n\n"

                                    # Show validation results
                                    val_result = latest_iter.get('validation_result')
                                    if val_result:
                                        is_valid = val_result.get('is_valid', False)
                                        iteration_log += f"**Valid:** {'✅ Yes' if is_valid else '❌ No'}\n\n"

                                        errors = val_result.get('errors', [])
                                        if errors:
                                            iteration_log += "**Errors:**\n"
                                            for err in errors[:3]:  # Show first 3 errors
                                                iteration_log += f"- `{err}`\n"
                                            if len(errors) > 3:
                                                iteration_log += f"- _...and {len(errors) - 3} more errors_\n"
                                            iteration_log += "\n"

                                    iteration_log += "---\n\n"

                                # Update final code
                                final_code = data.get("generated_code", final_code)
                                final_validation = data.get("validation_result", final_validation)
                                final_status = status

                            elif event_type == "complete":
                                session_id = data.get("session_id", session_id)
                                final_status = data.get("status", "")
                                final_code = data.get("generated_code", final_code)
                                final_validation = data.get("validation_result", final_validation)
                                current_iter = data.get("current_iteration", current_iter)

                                iteration_log += f"\n## ✅ Workflow Complete!\n\n"
                                iteration_log += f"**Final Status:** {final_status}\n\n"
                                iteration_log += f"**Total Iterations:** {current_iter}\n\n"

                            elif event_type == "error":
                                error_msg = data.get("error", "Unknown error")
                                iteration_log += f"\n## ❌ Error Occurred\n\n{error_msg}\n\n"

                        except json.JSONDecodeError:
                            pass  # Skip malformed JSON

            progress(1.0, desc="✅ Complete!")

            # Format final status
            status_emoji = {
                "success": "✅",
                "max_iterations_reached": "⚠️",
                "failed": "❌",
                "generating": "🔄",
                "validating": "🔍",
                "refining": "🔧"
            }.get(final_status, "ℹ️")

            status_text = f"""## {status_emoji} Session Status

**Session ID:** `{session_id}`

**Status:** {final_status.replace('_', ' ').title()}

**Iterations Completed:** {current_iter} / {max_iterations}

**Complete:** Yes
"""

            # Format validation info
            validation_text = "## 🔍 Final Validation Results\n\n"
            if final_validation:
                is_valid = final_validation.get("is_valid", False)
                errors = final_validation.get("errors", [])
                warnings = final_validation.get("warnings", [])

                validation_text += f"**Valid Code:** {'✅ Yes' if is_valid else '❌ No'}\n\n"

                if errors:
                    validation_text += "### ❌ Errors Found:\n"
                    for i, error in enumerate(errors, 1):
                        validation_text += f"{i}. `{error}`\n"
                    validation_text += "\n"

                if warnings:
                    validation_text += "### ⚠️ Warnings:\n"
                    for i, warning in enumerate(warnings, 1):
                        validation_text += f"{i}. `{warning}`\n"
                    validation_text += "\n"

                if is_valid:
                    validation_text += "### 🎉 Code is ready to render!\n\n"
                    validation_text += "Click **'Render Video'** below to create your animation."
                else:
                    validation_text += "### 🔧 Manual Editing Available\n\n"
                    validation_text += "Edit the code below and click **'Validate & Update Code'** to fix errors."
            else:
                validation_text += "*No validation results available*"

            return (
                status_text,
                final_code or "# No code generated yet",
                validation_text,
                session_id,
                iteration_log
            )

    except httpx.TimeoutException:
        error_msg = "❌ **Timeout Error:**\n\nThe request took too long."
        return error_msg, "", "", "", ""
    except httpx.ConnectError:
        error_msg = f"❌ **Connection Error:**\n\nCannot connect to API at {API_URL}"
        return error_msg, "", "", "", ""
    except Exception as e:
        error_msg = f"❌ **Unexpected Error:**\n\n{str(e)}"
        return error_msg, "", "", "", ""


async def validate_and_update_code(
    session_id: str,
    edited_code: str,
    progress=gr.Progress()
) -> Tuple[str, str]:
    """
    Validate and update manually edited code in a session.
    """
    if not session_id:
        return "❌ **Error:** No session ID available", ""

    if not edited_code or not edited_code.strip():
        return "❌ **Error:** No code provided", ""

    progress(0.0, desc="🔍 Validating code...")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_URL}/session/update-code",
                json={
                    "session_id": session_id,
                    "code": edited_code,
                    "validate": True
                }
            )

            if response.status_code == 404:
                return f"❌ **Error:** Session `{session_id}` not found", ""

            if response.status_code != 200:
                error_detail = response.json().get("detail", "Unknown error")
                return f"❌ **Error:** {error_detail}", ""

            result = response.json()
            is_valid = result.get("is_valid", False)
            validation_result = result.get("validation_result", {})
            message = result.get("message", "")

            progress(1.0, desc="✅ Complete!")

            # Format validation results
            validation_text = f"## {'✅' if is_valid else '❌'} Validation Results\n\n"
            validation_text += f"**Message:** {message}\n\n"

            if validation_result:
                errors = validation_result.get("errors", [])
                warnings = validation_result.get("warnings", [])

                if errors:
                    validation_text += "### ❌ Errors:\n"
                    for i, error in enumerate(errors, 1):
                        validation_text += f"{i}. `{error}`\n"
                    validation_text += "\n"

                if warnings:
                    validation_text += "### ⚠️ Warnings:\n"
                    for i, warning in enumerate(warnings, 1):
                        validation_text += f"{i}. `{warning}`\n"
                    validation_text += "\n"

                if is_valid:
                    validation_text += "### 🎉 Code is now valid and ready to render!\n\n"
                    validation_text += "Click **'Render Video'** to create your animation."
                else:
                    validation_text += "### 🔧 Please fix the errors and validate again.\n"

            # Return validation status as first output for the status display
            status_indicator = "✅ **Code Updated Successfully!**" if is_valid else "⚠️ **Code Updated (Still Has Errors)**"

            return status_indicator, validation_text

    except httpx.ConnectError:
        return f"❌ **Connection Error:** Cannot connect to API at {API_URL}", ""
    except Exception as e:
        return f"❌ **Error:** {str(e)}", ""


async def render_from_session(
    session_id: str,
    format: str,
    quality: str,
    background_color: str,
    include_subtitles: bool,
    progress=gr.Progress()
) -> Tuple[Optional[str], str]:
    """
    Render video from a session's validated code.
    Uses /session/render and /session/download endpoints.
    """
    if not session_id:
        return None, "❌ **Error:** Please generate code first to get a session ID"

    if not session_id.strip():
        return None, "❌ **Error:** Session ID is empty"

    progress(0.0, desc="🎬 Starting render...")

    # Log the render request
    print(f"\n[Gradio] Render request:")
    print(f"  - Session ID: {session_id}")
    print(f"  - Format: {format}")
    print(f"  - Quality: {quality}")
    print(f"  - Background: {background_color}")
    print(f"  - Include Subtitles: {include_subtitles}")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # First, check session status to verify it has valid code
            progress(0.1, desc="🔍 Verifying session...")

            status_response = await client.get(
                f"{API_URL}/session/status/{session_id}"
            )

            if status_response.status_code == 404:
                return None, f"❌ **Error:** Session `{session_id}` not found. It may have been deleted."

            if status_response.status_code != 200:
                error_detail = status_response.json().get("detail", "Unknown error")
                return None, f"❌ **Error:** Cannot verify session: {error_detail}"

            session_info = status_response.json()
            if not session_info.get("final_code"):
                return None, f"❌ **Error:** Session has no validated code. Please generate valid code first.\n\nSession status: {session_info.get('status', 'unknown')}"

            # Render video
            progress(0.2, desc="🎨 Rendering video with Manim...")

            response = await client.post(
                f"{API_URL}/session/render",
                json={
                    "session_id": session_id,
                    "format": format,
                    "quality": quality,
                    "background_color": background_color,
                    "include_subtitles": include_subtitles,
                }
            )

            if response.status_code == 400:
                error_detail = response.json().get("detail", "Unknown error")
                return None, f"❌ **Render Error:**\n\n{error_detail}"

            if response.status_code != 200:
                error_detail = response.json().get("detail", "Unknown error")
                return None, f"❌ **API Error ({response.status_code}):**\n\n{error_detail}"

            result = response.json()
            video_path = result.get("video_path")

            if not video_path:
                return None, "❌ **Error:** No video path in response"

            # Download the video
            progress(0.6, desc="⬇️ Downloading video...")

            video_response = await client.get(
                f"{API_URL}/session/download",
                params={"video_path": video_path}
            )

            if video_response.status_code != 200:
                return None, f"❌ **Download Error:** Status code {video_response.status_code}"

            # Save video locally
            progress(0.9, desc="💾 Saving video...")

            # Create unique filename with session ID
            file_ext = Path(video_path).suffix
            filename = f"session_{session_id[:8]}_{format}{file_ext}"
            local_path = Path(f"./generated_videos/{filename}")
            local_path.parent.mkdir(exist_ok=True)

            with open(local_path, "wb") as f:
                f.write(video_response.content)

            video_size = len(video_response.content)

            progress(1.0, desc="✅ Complete!")

            # Check if subtitles were included
            subtitle_indicator = ""
            if include_subtitles:
                if "_subtitled" in str(video_path):
                    subtitle_indicator = "\n\n📝 **Subtitles:** ✅ Included (AI-generated narration)"
                else:
                    subtitle_indicator = "\n\n📝 **Subtitles:** ⚠️ Requested but may have failed (check server logs)"

            success_msg = f"""✅ **Video Rendered Successfully!**

**File:** `{local_path}`

**Size:** {video_size / 1024:.2f} KB

**Format:** {format.upper()}

**Quality:** {quality}

**Session:** `{session_id[:16]}...`{subtitle_indicator}
"""
            return str(local_path), success_msg

    except httpx.TimeoutException:
        return None, "❌ **Timeout Error:** Video rendering took too long. Try a lower quality setting."
    except httpx.ConnectError:
        return None, f"❌ **Connection Error:** Cannot connect to API at {API_URL}"
    except Exception as e:
        return None, f"❌ **Unexpected Error:**\n\n{str(e)}"


async def check_api_health() -> str:
    """Check if the API is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_URL}/health")
            if response.status_code == 200:
                return "API is healthy and running"
            return f"API returned status code: {response.status_code}"
    except Exception as e:
        return f"API is not reachable: {str(e)}\n\nMake sure the FastAPI server is running on {API_URL}"


# Create Gradio interface
with gr.Blocks(title="Manim GPT - AI Video Generator", theme=gr.themes.Soft()) as app:
    gr.Markdown(
        """
        # Manim GPT - AI-Powered Video Generation

        Generate animated Manim videos from natural language prompts using AI.
        """
    )

    # API Health Status
    with gr.Row():
        with gr.Column(scale=3):
            health_status = gr.Textbox(label="API Status", interactive=False)
        with gr.Column(scale=1):
            health_btn = gr.Button("Check API Health", size="sm")

    health_btn.click(
        fn=check_api_health,
        outputs=health_status
    )

    # Main Content - Iterative Refinement with Streaming
    with gr.Column():
        gr.Markdown("""### Generate code with automatic error detection and refinement

This mode uses LangGraph to iteratively generate and validate code, automatically fixing errors until valid code is produced.
**New:** Real-time iteration logs and manual code editing support!""")

        with gr.Row():
            with gr.Column():
                iter_prompt = gr.Textbox(
                    label="Prompt",
                    placeholder="Example: Create an animation of a rotating cube with changing colors",
                    lines=3
                )

                with gr.Accordion("Settings", open=True):
                    with gr.Row():
                        iter_provider = gr.Dropdown(
                            choices=["Popular Models"] + get_providers(),
                            value="Popular Models",
                            label="Provider",
                            scale=1
                        )
                        iter_model = gr.Dropdown(
                            choices=POPULAR_MODELS,
                            value=DEFAULT_MODEL,
                            label="Model (or type custom)",
                            allow_custom_value=True,
                            scale=2
                        )
                    iter_temperature = gr.Slider(
                        minimum=0.0,
                        maximum=2.0,
                        value=0.7,
                        step=0.1,
                        label="Temperature"
                    )
                    iter_max_tokens = gr.Slider(
                        minimum=500,
                        maximum=4000,
                        value=2000,
                        step=100,
                        label="Max Tokens"
                    )
                    iter_max_iterations = gr.Slider(
                        minimum=1,
                        maximum=10,
                        value=5,
                        step=1,
                        label="Max Refinement Iterations"
                    )

                # Add event handler for provider change
                iter_provider.change(
                    fn=get_models_by_provider,
                    inputs=[iter_provider],
                    outputs=[iter_model]
                )

                generate_iter_btn = gr.Button("🚀 Generate with Streaming", variant="primary", size="lg")

            with gr.Column():
                iter_status = gr.Markdown("Status will appear here...")
                iter_validation = gr.Markdown("Validation results will appear here...")

        # Iteration Log Viewer
        with gr.Accordion("📊 Iteration Log (Real-time)", open=False):
            iter_log = gr.Markdown("Iteration details will appear here during generation...")

        # Code Editor Section with Manual Editing Support
        with gr.Row():
            with gr.Column(scale=2):
                iter_code_output = gr.Code(
                    label="Generated Code (Editable - You can fix errors manually!)",
                    language="python",
                    lines=20
                )

                # Manual validation section
                with gr.Row():
                    validate_code_btn = gr.Button("🔍 Validate & Update Code", variant="secondary")
                    validate_status = gr.Textbox(label="Validation Status", interactive=False, lines=1)

                validate_results = gr.Markdown("Manual validation results will appear here...")

            with gr.Column(scale=1):
                iter_session_id = gr.Textbox(
                    label="Session ID",
                    interactive=False
                )

                gr.Markdown("### Render Settings")

                with gr.Row():
                    render_format = gr.Dropdown(
                        choices=["mp4", "webm", "gif", "mov"],
                        value="mp4",
                        label="Format"
                    )
                    render_quality = gr.Dropdown(
                        choices=["low", "medium", "high", "4k"],
                        value="medium",
                        label="Quality"
                    )

                render_bg_color = gr.Textbox(
                    value="#000000",
                    label="Background Color"
                )

                render_subtitles = gr.Checkbox(
                    value=True,
                    label="📝 Include AI-Generated Subtitles",
                    info="Add educational narration that explains the animation (requires LLM API key)"
                )

                render_btn = gr.Button("🎬 Render Video", variant="primary", size="lg")

                iter_video_output = gr.Video(label="Rendered Video")
                iter_render_status = gr.Markdown("Render status will appear here...")

        # Connect iterative generation with streaming
        generate_iter_btn.click(
            fn=iterative_generate_streaming,
            inputs=[
                iter_prompt,
                iter_model,
                iter_temperature,
                iter_max_tokens,
                iter_max_iterations
            ],
            outputs=[iter_status, iter_code_output, iter_validation, iter_session_id, iter_log]
        )

        # Connect manual code validation
        validate_code_btn.click(
            fn=validate_and_update_code,
            inputs=[iter_session_id, iter_code_output],
            outputs=[validate_status, validate_results]
        )

        # Connect rendering
        render_btn.click(
            fn=render_from_session,
            inputs=[
                iter_session_id,
                render_format,
                render_quality,
                render_bg_color,
                render_subtitles
            ],
            outputs=[iter_video_output, iter_render_status]
        )

        # Example prompts
        gr.Markdown("### Example Prompts")
        gr.Examples(
            examples=[
                ["Create an animation showing the derivative of x squared"],
                ["Animate a sine wave transforming into a cosine wave"],
                ["Show a bouncing ball with physics"],
                ["Demonstrate the Pythagorean theorem with a right triangle"],
                ["Create a bar chart that animates upward"],
                ["Visualize matrix multiplication step by step"],
                ["Show quicksort algorithm with an array of numbers"],
            ],
            inputs=iter_prompt,
        )

        gr.Markdown("""
        ### How it works:
        1. **Generate with Streaming** - The system will:
           - 🔄 Stream real-time progress updates for each iteration
           - 📝 Generate initial Manim code
           - 🔍 Validate it (syntax + Manim dry-run)
           - 🔧 If errors found, automatically refine and retry
           - ♻️ Repeat until valid or max iterations reached
           - 📊 Show detailed logs for every iteration

        2. **Manual Code Editing** - If max iterations is reached with errors:
           - ✏️ Edit the code directly in the code editor
           - 🔍 Click "Validate & Update Code" to check your fixes
           - ✅ System will validate and update the session
           - 🎬 Once valid, you can render the video

        3. **Render Video** - Once you have valid code (session ID will appear), you can render it
           - 📝 **NEW: Code Narration Subtitles** - Enable to automatically generate educational subtitles that explain the animation

        ### New Features:
        - 📝 **Code Narration Subtitles** - AI-generated subtitles that narrate what's happening in the animation
        - 📊 **Real-time Iteration Logs** - See each iteration's code, errors, and status as they happen
        - ✏️ **Manual Code Editing** - Fix errors yourself after automatic refinement completes
        - 🔄 **Streaming Updates** - Watch the workflow progress in real-time
        - 🔍 **Instant Validation** - Validate your manual edits before rendering

        ### Benefits:
        - 🔄 Automatic error correction with streaming progress
        - ✏️ Manual intervention when needed
        - ✅ Validated code before rendering
        - 📊 Full visibility into every iteration with detailed logs
        - 💾 Session-based workflow
        - 📝 Educational narration for better understanding
        """)

    # Help Section
    with gr.Accordion("Help & Documentation", open=False):
        gr.Markdown(
            """
            ## How to Use

            ### Iterative Refinement Workflow
            1. **Enter Your Prompt**: Describe the animation you want to create
            2. **Configure Settings**:
               - Select your LLM model and provider
               - Adjust temperature (0.3-0.5 for consistency, 0.7-1.0 for creativity)
               - Set max tokens and max refinement iterations
            3. **Generate with Refinement**: Click the button to start the LangGraph workflow
               - The system generates initial Manim code
               - Validates it (syntax + Manim dry-run)
               - If errors found, automatically refines and retries
               - Repeats until valid or max iterations reached
            4. **Review Results**: Check the status, validation results, and generated code
            5. **Render Video**: Once validation passes, configure video settings and click "Render Video"

            ## Quality Presets

            | Quality | Resolution | Frame Rate | Use Case |
            |---------|-----------|------------|----------|
            | Low | 480p | 15 fps | Quick previews |
            | Medium | 720p | 30 fps | Standard quality |
            | High | 1080p | 60 fps | High quality |
            | 4K | 2160p | 60 fps | Professional |

            ## Model Selection

            - **Provider**: Select a specific LLM provider (OpenAI, Anthropic, Google, etc.) or use "Popular Models"
            - **Model**: Choose from available models for the selected provider, or type a custom model name
            - Models are fetched dynamically from the API based on your selection

            ## Tips

            - Be specific in your prompts for better results
            - Use mathematical or geometric terms when applicable
            - For complex animations, break them into steps
            - Lower temperature (0.3-0.5) for more consistent code
            - Higher temperature (0.7-1.0) for more creative variations
            - Different models may produce different code styles - experiment to find what works best
            - Start with 5 max iterations and increase if needed for complex animations

            ## Troubleshooting

            - **API not reachable**: Make sure the FastAPI server is running on `{}`
            - **Generation takes too long**: Try lower quality settings first or reduce max iterations
            - **Max iterations reached**: The code may still have errors; try increasing max iterations or simplifying your prompt
            - **Session not found**: Sessions may expire; regenerate the code

            ## API Server

            Before using this UI, make sure to start the FastAPI server:

            ```bash
            uv run main.py
            ```

            Or with uvicorn:

            ```bash
            uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
            ```
            """.format(API_URL)
        )


def launch_app(share: bool = False, server_name: str = "0.0.0.0", server_port: int = None):
    """Launch the Gradio application."""
    # Create output directory
    Path("./generated_videos").mkdir(exist_ok=True)

    # Use PORT environment variable if set (for IDX), otherwise default to 7860
    if server_port is None:
        server_port = int(os.getenv("PORT", "7860"))

    print(f"\nMaking sure API is running at {API_URL}...")
    print("If the API is not running, start it with: uv run main.py\n")

    app.launch(
        share=share,
        server_name=server_name,
        server_port=server_port,
        show_error=True
    )


if __name__ == "__main__":
    launch_app()
