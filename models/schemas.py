from pydantic import BaseModel, Field
from typing import Optional, Literal


class CodeGenerationRequest(BaseModel):
    prompt: str
    model: Optional[str] = "cerebras/zai-glm-4.6"
    max_tokens: Optional[int] = 1000
    temperature: Optional[float] = 0.7


class CodeGenerationResponse(BaseModel):
    generated_code: str
    model_used: str


class VideoGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Description of the Manim animation to generate")
    format: Literal["mp4", "webm", "gif", "mov"] = Field(default="mp4", description="Output video format")
    quality: Literal["low", "medium", "high", "4k"] = Field(default="medium", description="Video quality preset")
    model: Optional[str] = Field(default="cerebras/zai-glm-4.6", description="LLM model for code generation")
    max_tokens: Optional[int] = Field(default=2000, description="Maximum tokens for code generation")
    temperature: Optional[float] = Field(default=0.7, description="Temperature for code generation")
    background_color: Optional[str] = Field(default=None, description="Background color (e.g., '#000000', 'WHITE')")
    include_subtitles: bool = Field(default=False, description="Generate and add narration subtitles to the video")
    subtitle_style: Optional[str] = Field(default=None, description="Custom subtitle style in ASS format")


class VideoGenerationResponse(BaseModel):
    video_path: str
    generated_code: str
    model_used: str
    format: str
    message: str
