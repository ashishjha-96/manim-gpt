from litellm import acompletion
from typing import Optional
import os


async def generate_manim_code(prompt: str, model: str, max_tokens: int, temperature: float, api_token: Optional[str] = None) -> tuple[str, str]:
    """
    Generate Manim animation code using LLM.

    Args:
        prompt: User's prompt for the animation
        model: LLM model to use
        max_tokens: Maximum tokens for generation
        temperature: Temperature for generation
        api_token: Optional API token for the provider

    Returns:
        tuple: (generated_code, model_used)
    """
    system_prompt = """You are an expert Manim (Mathematical Animation Engine) programmer.
Generate complete, working Manim code based on the user's request.

IMPORTANT REQUIREMENTS:
1. Use ManimCommunity syntax (from manim import *)
2. Create a Scene class that inherits from Scene
3. Use self.play() for animations and self.wait() for pauses
4. Include proper imports
5. The class name should be "GeneratedScene"
6. Only return Python code, no explanations or markdown formatting
7. Make the animations visually appealing and smooth
8. Use appropriate animation timing (self.wait() between animations)
9. Include comments to explain complex parts

Example structure:
```python
from manim import *

class GeneratedScene(Scene):
    def construct(self):
        # Your animation code here
        text = Text("Hello World")
        self.play(Write(text))
        self.wait()
```

Generate clean, working Manim code based on the user's request."""

    # Prepare acompletion parameters
    completion_params = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    # Add API key if provided
    if api_token:
        completion_params["api_key"] = api_token

    response = await acompletion(**completion_params)

    generated_code = response.choices[0].message.content.strip()

    # Clean up markdown formatting
    if generated_code.startswith("```python"):
        generated_code = generated_code[len("```python"):].strip()
    if generated_code.startswith("```"):
        generated_code = generated_code[3:].strip()
    if generated_code.endswith("```"):
        generated_code = generated_code[:-3].strip()

    return generated_code, model
