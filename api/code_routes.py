from fastapi import APIRouter, HTTPException
from litellm import acompletion

from models.schemas import CodeGenerationRequest, CodeGenerationResponse

router = APIRouter(prefix="/code", tags=["code"])


@router.post("/generate", response_model=CodeGenerationResponse)
async def generate_code(request: CodeGenerationRequest):
    """
    Generate Python code based on a user prompt using LiteLLM.

    Args:
        request: CodeGenerationRequest containing the prompt and optional parameters

    Returns:
        CodeGenerationResponse with the generated Python code
    """
    try:
        # Create the system prompt to guide code generation
        system_prompt = """You are an expert Python programmer. Generate clean, efficient,
        and well-documented Python code based on the user's request. Include docstrings
        and comments where appropriate. Only return the Python code without any additional
        explanation or markdown formatting."""

        # Call LiteLLM async completion
        response = await acompletion(
            model=request.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.prompt}
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        # Extract the generated code from the response
        generated_code = response.choices[0].message.content.strip()

        # Remove markdown code blocks if present
        if generated_code.startswith("```python"):
            generated_code = generated_code[len("```python"):].strip()
        if generated_code.startswith("```"):
            generated_code = generated_code[3:].strip()
        if generated_code.endswith("```"):
            generated_code = generated_code[:-3].strip()

        return CodeGenerationResponse(
            generated_code=generated_code,
            model_used=request.model
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating code: {str(e)}"
        )


@router.post("/generate-manim", response_model=CodeGenerationResponse)
async def generate_manim_code_only(request: CodeGenerationRequest):
    """
    Generate only Manim code without rendering the video.

    Args:
        request: CodeGenerationRequest with prompt and generation options

    Returns:
        CodeGenerationResponse with generated Manim code
    """
    try:
        # Modified system prompt for Manim-specific code generation
        system_prompt = """You are an expert Manim (Mathematical Animation Engine) programmer.
Generate complete, working Manim code based on the user's request.

IMPORTANT REQUIREMENTS:
1. Use ManimCommunity syntax (from manim import *)
2. Create a Scene class that inherits from Scene
3. Use self.play() for animations and self.wait() for pauses
4. Include proper imports
5. Make the class name descriptive or use "GeneratedScene"
6. Only return Python code, no explanations or markdown formatting
7. Make the animations visually appealing and smooth
8. Use appropriate animation timing
9. Include comments to explain complex parts

Generate clean, working Manim code based on the user's request."""

        response = await acompletion(
            model=request.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.prompt}
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        generated_code = response.choices[0].message.content.strip()

        # Clean up markdown formatting
        if generated_code.startswith("```python"):
            generated_code = generated_code[len("```python"):].strip()
        if generated_code.startswith("```"):
            generated_code = generated_code[3:].strip()
        if generated_code.endswith("```"):
            generated_code = generated_code[:-3].strip()

        return CodeGenerationResponse(
            generated_code=generated_code,
            model_used=request.model
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating Manim code: {str(e)}"
        )
