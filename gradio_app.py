"""
Gradio UI for Manim GPT - AI-Powered Video Generation
"""
import gradio as gr
import httpx
import os
from pathlib import Path
import asyncio
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


async def generate_video(
    prompt: str,
    format: str,
    quality: str,
    model: str,
    temperature: float,
    max_tokens: int,
    background_color: str,
    progress=gr.Progress()
) -> Tuple[Optional[str], str, str]:
    """Generate a Manim video from a text prompt."""
    if not prompt:
        return None, "Please enter a prompt", ""

    progress(0.1, desc="Sending request to API...")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Generate video
            progress(0.2, desc="Generating Manim code...")
            response = await client.post(
                f"{API_URL}/video/generate",
                json={
                    "prompt": prompt,
                    "format": format,
                    "quality": quality,
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "background_color": background_color,
                }
            )

            if response.status_code != 200:
                error_msg = response.json().get("detail", "Unknown error")
                return None, f"Error: {error_msg}", ""

            result = response.json()
            video_path = result.get("video_path")
            generated_code = result.get("generated_code", "")

            if not video_path:
                return None, "Error: No video path in response", generated_code

            # Download the video
            progress(0.7, desc="Downloading video...")
            video_response = await client.get(
                f"{API_URL}/video/download",
                params={"video_path": video_path}
            )

            if video_response.status_code != 200:
                return None, f"Error downloading video: {video_response.status_code}", generated_code

            # Save video locally
            progress(0.9, desc="Saving video...")
            local_path = Path(f"./generated_videos/{Path(video_path).name}")
            local_path.parent.mkdir(exist_ok=True)

            with open(local_path, "wb") as f:
                f.write(video_response.content)

            progress(1.0, desc="Complete!")
            return str(local_path), f"Video generated successfully!", generated_code

    except httpx.TimeoutException:
        return None, "Error: Request timed out. The video generation may take a while.", ""
    except Exception as e:
        return None, f"Error: {str(e)}", ""


async def generate_code_only(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    progress=gr.Progress()
) -> str:
    """Generate only Manim code without rendering."""
    if not prompt:
        return "Please enter a prompt"

    progress(0.3, desc="Generating code...")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{API_URL}/code/generate-manim",
                json={
                    "prompt": prompt,
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
            )

            if response.status_code != 200:
                error_msg = response.json().get("detail", "Unknown error")
                return f"Error: {error_msg}"

            result = response.json()
            progress(1.0, desc="Complete!")
            return result.get("generated_code", "No code generated")

    except Exception as e:
        return f"Error: {str(e)}"


async def iterative_generate(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    max_iterations: int,
    progress=gr.Progress()
) -> Tuple[str, str, str, str]:
    """
    Generate Manim code with iterative refinement using session API.
    This function calls the /session/generate endpoint which runs the full
    LangGraph workflow with automatic validation and refinement.
    """
    if not prompt:
        return "❌ **Error:** Please enter a prompt", "", "", ""

    progress(0.0, desc="🚀 Starting session...")

    try:
        async with httpx.AsyncClient(timeout=600.0) as client:
            # Start iterative generation session
            progress(0.1, desc="📝 Creating session and running workflow...")

            response = await client.post(
                f"{API_URL}/session/generate",
                json={
                    "prompt": prompt,
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "max_iterations": max_iterations,
                }
            )

            if response.status_code != 200:
                error_detail = response.json().get("detail", "Unknown error")
                error_msg = f"❌ **API Error ({response.status_code}):**\n\n{error_detail}"
                return error_msg, "", "", ""

            result = response.json()
            session_id = result.get("session_id")
            status = result.get("status")
            current_iteration = result.get("current_iteration")
            generated_code = result.get("generated_code", "")
            validation_result = result.get("validation_result", {})
            message = result.get("message", "")
            is_complete = result.get("is_complete", False)

            progress(0.8, desc="✅ Workflow complete, processing results...")

            # Determine status emoji
            status_emoji = {
                "success": "✅",
                "max_iterations_reached": "⚠️",
                "failed": "❌",
                "generating": "🔄",
                "validating": "🔍",
                "refining": "🔧"
            }.get(status, "ℹ️")

            # Format status info with better styling
            status_text = f"""## {status_emoji} Session Status

**Session ID:** `{session_id}`

**Status:** {status.replace('_', ' ').title()}

**Iterations Completed:** {current_iteration} / {max_iterations}

**Message:** {message}

**Complete:** {'Yes' if is_complete else 'No'}
"""

            # Format validation info with better styling
            validation_text = "## 🔍 Validation Results\n\n"
            if validation_result:
                is_valid = validation_result.get("is_valid", False)
                errors = validation_result.get("errors", [])
                warnings = validation_result.get("warnings", [])

                validation_text += f"**Valid Code:** {'✅ Yes' if is_valid else '❌ No'}\n\n"

                if errors:
                    validation_text += "### ❌ Errors Found:\n"
                    for i, error in enumerate(errors[:5], 1):  # Show max 5 errors
                        validation_text += f"{i}. `{error}`\n"
                    if len(errors) > 5:
                        validation_text += f"\n_...and {len(errors) - 5} more errors_\n"
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
                validation_text += "*No validation results available*"

            progress(1.0, desc="✅ Complete!")

            # Return formatted results
            return (
                status_text,
                generated_code or "# No code generated yet",
                validation_text,
                session_id
            )

    except httpx.TimeoutException:
        error_msg = "❌ **Timeout Error:**\n\nThe request took too long. The workflow may still be running on the server."
        return error_msg, "", "", ""
    except httpx.ConnectError:
        error_msg = f"❌ **Connection Error:**\n\nCannot connect to API at {API_URL}\n\nMake sure the server is running."
        return error_msg, "", "", ""
    except Exception as e:
        error_msg = f"❌ **Unexpected Error:**\n\n{str(e)}"
        return error_msg, "", "", ""


async def render_from_session(
    session_id: str,
    format: str,
    quality: str,
    background_color: str,
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

            success_msg = f"""✅ **Video Rendered Successfully!**

**File:** `{local_path}`

**Size:** {video_size / 1024:.2f} KB

**Format:** {format.upper()}

**Quality:** {quality}

**Session:** `{session_id[:16]}...`
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

    with gr.Tabs():
        # Video Generation Tab
        with gr.TabItem("Generate Video"):
            gr.Markdown("### Create a complete animated video from your prompt")

            with gr.Row():
                with gr.Column():
                    video_prompt = gr.Textbox(
                        label="Prompt",
                        placeholder="Example: Create an animation showing the Pythagorean theorem with a right triangle",
                        lines=3
                    )

                    with gr.Row():
                        video_format = gr.Dropdown(
                            choices=["mp4", "webm", "gif", "mov"],
                            value="mp4",
                            label="Format"
                        )
                        video_quality = gr.Dropdown(
                            choices=["low", "medium", "high", "4k"],
                            value="medium",
                            label="Quality"
                        )

                    with gr.Accordion("Advanced Settings", open=False):
                        with gr.Row():
                            video_provider = gr.Dropdown(
                                choices=["Popular Models"] + get_providers(),
                                value="Popular Models",
                                label="Provider",
                                scale=1
                            )
                            video_model = gr.Dropdown(
                                choices=POPULAR_MODELS,
                                value=DEFAULT_MODEL,
                                label="Model (or type custom)",
                                allow_custom_value=True,
                                scale=2
                            )
                        video_temperature = gr.Slider(
                            minimum=0.0,
                            maximum=2.0,
                            value=0.7,
                            step=0.1,
                            label="Temperature"
                        )
                        video_max_tokens = gr.Slider(
                            minimum=500,
                            maximum=4000,
                            value=2000,
                            step=100,
                            label="Max Tokens"
                        )
                        video_bg_color = gr.Textbox(
                            value="#000000",
                            label="Background Color (hex or Manim color name)"
                        )

                    # Add event handler for provider change
                    video_provider.change(
                        fn=get_models_by_provider,
                        inputs=[video_provider],
                        outputs=[video_model]
                    )

                    generate_video_btn = gr.Button("Generate Video", variant="primary", size="lg")

                with gr.Column():
                    video_output = gr.Video(label="Generated Video")
                    video_status = gr.Textbox(label="Status", lines=2)
                    video_code_output = gr.Code(
                        label="Generated Manim Code",
                        language="python",
                        lines=15
                    )

            generate_video_btn.click(
                fn=generate_video,
                inputs=[
                    video_prompt,
                    video_format,
                    video_quality,
                    video_model,
                    video_temperature,
                    video_max_tokens,
                    video_bg_color
                ],
                outputs=[video_output, video_status, video_code_output]
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
                inputs=video_prompt,
            )

        # Code Generation Tab
        with gr.TabItem("Generate Code Only"):
            gr.Markdown("### Generate Manim code without rendering the video")

            with gr.Row():
                with gr.Column():
                    code_prompt = gr.Textbox(
                        label="Prompt",
                        placeholder="Example: Create code for animating a pendulum",
                        lines=3
                    )

                    with gr.Accordion("Settings", open=True):
                        with gr.Row():
                            code_provider = gr.Dropdown(
                                choices=["Popular Models"] + get_providers(),
                                value="Popular Models",
                                label="Provider",
                                scale=1
                            )
                            code_model = gr.Dropdown(
                                choices=POPULAR_MODELS,
                                value=DEFAULT_MODEL,
                                label="Model (or type custom)",
                                allow_custom_value=True,
                                scale=2
                            )
                        code_temperature = gr.Slider(
                            minimum=0.0,
                            maximum=2.0,
                            value=0.7,
                            step=0.1,
                            label="Temperature"
                        )
                        code_max_tokens = gr.Slider(
                            minimum=500,
                            maximum=4000,
                            value=1000,
                            step=100,
                            label="Max Tokens"
                        )

                    # Add event handler for provider change
                    code_provider.change(
                        fn=get_models_by_provider,
                        inputs=[code_provider],
                        outputs=[code_model]
                    )

                    generate_code_btn = gr.Button("Generate Code", variant="primary", size="lg")

                with gr.Column():
                    code_output = gr.Code(
                        label="Generated Code",
                        language="python",
                        lines=20
                    )

            generate_code_btn.click(
                fn=generate_code_only,
                inputs=[
                    code_prompt,
                    code_model,
                    code_temperature,
                    code_max_tokens
                ],
                outputs=code_output
            )

        # Iterative Refinement Tab
        with gr.TabItem("Iterative Refinement ⚡"):
            gr.Markdown("""### Generate code with automatic error detection and refinement

This mode uses LangGraph to iteratively generate and validate code, automatically fixing errors until valid code is produced.""")

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

                    generate_iter_btn = gr.Button("Generate with Refinement", variant="primary", size="lg")

                with gr.Column():
                    iter_status = gr.Markdown("Status will appear here...")
                    iter_validation = gr.Markdown("Validation results will appear here...")

            # Code and rendering section
            with gr.Row():
                with gr.Column():
                    iter_code_output = gr.Code(
                        label="Generated & Validated Code",
                        language="python",
                        lines=20
                    )

                with gr.Column():
                    iter_session_id = gr.Textbox(
                        label="Session ID (for rendering)",
                        interactive=False
                    )

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

                    render_btn = gr.Button("Render Video", variant="secondary", size="lg")

                    iter_video_output = gr.Video(label="Rendered Video")
                    iter_render_status = gr.Textbox(label="Render Status", lines=2)

            # Connect iterative generation
            generate_iter_btn.click(
                fn=iterative_generate,
                inputs=[
                    iter_prompt,
                    iter_model,
                    iter_temperature,
                    iter_max_tokens,
                    iter_max_iterations
                ],
                outputs=[iter_status, iter_code_output, iter_validation, iter_session_id]
            )

            # Connect rendering
            render_btn.click(
                fn=render_from_session,
                inputs=[
                    iter_session_id,
                    render_format,
                    render_quality,
                    render_bg_color
                ],
                outputs=[iter_video_output, iter_render_status]
            )

            gr.Markdown("""
            ### How it works:
            1. **Generate with Refinement** - The system will:
               - Generate initial Manim code
               - Validate it (syntax + Manim dry-run)
               - If errors found, automatically refine and retry
               - Repeat until valid or max iterations reached

            2. **Render Video** - Once you have valid code (session ID will appear), you can render it

            ### Benefits:
            - 🔄 Automatic error correction
            - ✅ Validated code before rendering
            - 📊 Full visibility into iterations and errors
            - 💾 Session-based workflow
            """)

        # Help Tab
        with gr.TabItem("Help"):
            gr.Markdown(
                """
                ## How to Use

                ### Generate Video
                1. Enter a description of the animation you want to create
                2. Select your desired format (MP4, WebM, GIF, or MOV)
                3. Choose quality level (low/medium/high/4k)
                4. Click "Generate Video"
                5. Wait for the video to be generated and rendered

                ### Generate Code Only
                - Use this if you want to see the Manim code without rendering
                - Faster than generating the full video
                - You can copy and modify the code for your own use

                ### Iterative Refinement (Recommended) ⚡
                - Uses LangGraph for automatic error detection and correction
                - Generates code, validates it, and automatically refines if errors are found
                - Repeats until valid code is produced or max iterations reached
                - Shows full visibility into each iteration, errors, and fixes
                - Two-step process: Generate & Validate → Render Video
                - Best for complex animations or when you want reliable code

                ## Quality Presets

                | Quality | Resolution | Frame Rate | Use Case |
                |---------|-----------|------------|----------|
                | Low | 480p | 15 fps | Quick previews |
                | Medium | 720p | 30 fps | Standard quality |
                | High | 1080p | 60 fps | High quality |
                | 4K | 2160p | 60 fps | Professional |

                ## Advanced Settings

                ### Model Selection
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

                ## Troubleshooting

                - **API not reachable**: Make sure the FastAPI server is running on `{}`
                - **Generation takes too long**: Try lower quality settings first
                - **Code errors**: Try regenerating with a more specific prompt

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
