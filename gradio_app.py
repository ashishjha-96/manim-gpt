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
                        video_model = gr.Dropdown(
                            choices=POPULAR_MODELS,
                            value=DEFAULT_MODEL,
                            label="Model",
                            allow_custom_value=True
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
                        code_model = gr.Dropdown(
                            choices=POPULAR_MODELS,
                            value=DEFAULT_MODEL,
                            label="Model",
                            allow_custom_value=True
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

                ## Quality Presets

                | Quality | Resolution | Frame Rate | Use Case |
                |---------|-----------|------------|----------|
                | Low | 480p | 15 fps | Quick previews |
                | Medium | 720p | 30 fps | Standard quality |
                | High | 1080p | 60 fps | High quality |
                | 4K | 2160p | 60 fps | Professional |

                ## Tips

                - Be specific in your prompts for better results
                - Use mathematical or geometric terms when applicable
                - For complex animations, break them into steps
                - Lower temperature (0.3-0.5) for more consistent code
                - Higher temperature (0.7-1.0) for more creative variations

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
