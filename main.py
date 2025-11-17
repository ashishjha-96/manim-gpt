from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from litellm import acompletion
import litellm
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Enable LiteLLM debug mode
litellm.set_verbose = True

app = FastAPI(title="Python Code Generator API")


class CodeGenerationRequest(BaseModel):
    prompt: str
    model: Optional[str] = "cerebras/zai-glm-4.6"
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7


class CodeGenerationResponse(BaseModel):
    generated_code: str
    model_used: str


@app.get("/")
async def root():
    return {"message": "Python Code Generator API", "status": "running"}


@app.post("/generate-code", response_model=CodeGenerationResponse)
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


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
