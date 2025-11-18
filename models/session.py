"""
Session models for iterative code generation and refinement.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class IterationStatus(str, Enum):
    """Status of a code generation iteration."""
    GENERATING = "generating"
    VALIDATING = "validating"
    REFINING = "refining"
    SUCCESS = "success"
    FAILED = "failed"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"


class RenderStatus(str, Enum):
    """Status of video rendering process."""
    QUEUED = "queued"
    PREPARING = "preparing"
    RENDERING_VIDEO = "rendering_video"
    GENERATING_SUBTITLES = "generating_subtitles"
    CREATING_SRT = "creating_srt"
    STITCHING_SUBTITLES = "stitching_subtitles"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationMetrics(BaseModel):
    """Metrics for code generation."""
    time_taken: float = Field(..., description="Time taken in seconds")
    prompt_tokens: Optional[int] = Field(default=None, description="Number of prompt tokens used")
    completion_tokens: Optional[int] = Field(default=None, description="Number of completion tokens generated")
    total_tokens: Optional[int] = Field(default=None, description="Total tokens used")
    model: Optional[str] = Field(default=None, description="Model used for generation")


class ValidationMetrics(BaseModel):
    """Metrics for code validation."""
    time_taken: float = Field(..., description="Time taken in seconds")


class RenderProgress(BaseModel):
    """Progress information for video rendering."""
    status: RenderStatus
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None


class CodeIteration(BaseModel):
    """Represents a single iteration of code generation."""
    iteration_number: int
    generated_code: str
    validation_result: Optional[dict] = None  # Contains is_valid, errors, warnings
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: IterationStatus
    generation_metrics: Optional[GenerationMetrics] = Field(default=None, description="Metrics from code generation")
    validation_metrics: Optional[ValidationMetrics] = Field(default=None, description="Metrics from validation")


class SessionState(BaseModel):
    """State maintained throughout a session."""
    session_id: str
    prompt: str
    model: str
    temperature: float
    max_tokens: int
    max_iterations: int = 5
    current_iteration: int = 0
    iterations: List[CodeIteration] = Field(default_factory=list)
    status: IterationStatus = IterationStatus.GENERATING
    final_code: Optional[str] = None
    rendered_video_path: Optional[str] = None  # Path to rendered video file

    # Render tracking
    render_status: Optional[RenderStatus] = None
    render_progress: List[RenderProgress] = Field(default_factory=list)
    render_started_at: Optional[datetime] = None
    render_completed_at: Optional[datetime] = None
    render_error: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class IterativeGenerationRequest(BaseModel):
    """Request to start an iterative generation session."""
    prompt: str = Field(..., description="Description of the Manim animation to generate")
    model: Optional[str] = Field(default="cerebras/llama3.1-8b", description="LLM model for code generation")
    max_tokens: Optional[int] = Field(default=2000, description="Maximum tokens for code generation")
    temperature: Optional[float] = Field(default=0.7, description="Temperature for code generation")
    max_iterations: Optional[int] = Field(default=5, description="Maximum number of refinement iterations")


class IterativeGenerationResponse(BaseModel):
    """Response from iterative generation."""
    session_id: str
    status: IterationStatus
    current_iteration: int
    generated_code: Optional[str] = None
    validation_result: Optional[dict] = None
    message: str
    is_complete: bool = False


class SessionContinueRequest(BaseModel):
    """Request to continue an existing session (e.g., after reviewing errors)."""
    session_id: str
    feedback: Optional[str] = Field(default=None, description="Additional feedback from user")


class SessionStatusResponse(BaseModel):
    """Response with current session status."""
    session_id: str
    status: IterationStatus
    current_iteration: int
    max_iterations: int
    iterations_history: List[CodeIteration]
    final_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class RenderRequest(BaseModel):
    """Request to render a validated code from session."""
    session_id: str
    format: Literal["mp4", "webm", "gif", "mov"] = Field(default="mp4", description="Output video format")
    quality: Literal["low", "medium", "high", "4k"] = Field(default="medium", description="Video quality preset")
    background_color: Optional[str] = Field(default=None, description="Background color")
    include_subtitles: bool = Field(default=False, description="Generate and add narration subtitles to the video")
    subtitle_style: Optional[str] = Field(default=None, description="Custom subtitle style in ASS format")
    subtitle_font_size: int = Field(default=24, description="Font size for subtitles (default: 24). Ignored if subtitle_style is provided.", ge=8, le=72)
    model: Optional[str] = Field(default="cerebras/zai-glm-4.6", description="LLM model for subtitle generation")


class ManualCodeUpdateRequest(BaseModel):
    """Request to manually update and validate code in a session."""
    session_id: str
    code: str = Field(..., description="Manually edited Manim code")
    should_validate: bool = Field(default=True, description="Whether to validate the code before updating", alias="validate")


class ManualCodeUpdateResponse(BaseModel):
    """Response from manual code update."""
    session_id: str
    code: str
    validation_result: Optional[dict] = None
    is_valid: bool = False
    message: str


class RenderStatusResponse(BaseModel):
    """Response for render status polling."""
    session_id: str
    render_status: RenderStatus
    progress: List[RenderProgress]
    video_path: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    elapsed_time: Optional[float] = None  # seconds since render started
