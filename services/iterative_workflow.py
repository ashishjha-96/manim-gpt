"""
LangGraph workflow for iterative Manim code generation and refinement.
"""
from typing import TypedDict, Annotated, Sequence, Callable, Optional, Any
from datetime import datetime
import operator
import asyncio
import time

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from litellm import acompletion
from services.code_validator import validate_code
from models.session import IterationStatus, CodeIteration, GenerationMetrics, ValidationMetrics
from utils.logger import get_logger, get_logger_with_session

# Create base loggers for workflow components (session-specific loggers will be created in nodes)
logger_workflow = get_logger("Workflow")


class WorkflowState(TypedDict):
    """State that gets passed between nodes in the workflow."""
    session_id: str
    prompt: str
    model: str
    temperature: float
    max_tokens: int
    max_iterations: int
    current_iteration: int
    messages: Annotated[Sequence[BaseMessage], operator.add]
    generated_code: str | None
    validation_result: dict | None
    iterations_history: list[CodeIteration]
    status: IterationStatus
    error_message: str | None
    # Metrics for current iteration
    generation_metrics: GenerationMetrics | None
    validation_metrics: ValidationMetrics | None


async def generate_code_node(state: WorkflowState) -> dict:
    """
    Node that generates Manim code using LLM.
    For first iteration, uses the original prompt.
    For refinements, includes error feedback.
    """
    # Create session-aware logger
    logger_generate = get_logger_with_session("Generate", state["session_id"])
    logger_generate.info(f"Iteration {state['current_iteration'] + 1}")

    # Build system prompt
    system_prompt = """You are an expert Manim (Mathematical Animation Engine) programmer.
Generate complete, working Manim code based on the user's request.

IMPORTANT REQUIREMENTS:
1. Use ManimCommunity syntax (from manim import *)
2. Create a Scene class that inherits from Scene
3. Use self.play() for animations and self.wait() for pauses
4. Include proper imports
5. The class name MUST be "GeneratedScene"
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

CRITICAL: If you receive error feedback, carefully analyze the errors and fix them.
Common issues to avoid:
- Missing imports
- Incorrect class/method names
- Invalid Manim objects or animations
- Syntax errors
- Undefined variables or attributes

Generate clean, working Manim code."""

    # Build user message based on iteration
    if state["current_iteration"] == 0:
        # First iteration - use original prompt
        user_message = state["prompt"]
    else:
        # Refinement - include error feedback
        last_iteration = state["iterations_history"][-1]
        validation = last_iteration.validation_result

        error_info = "\n".join(validation.get("errors", []))
        warnings_info = "\n".join(validation.get("warnings", []))

        user_message = f"""The previous code had errors. Please fix them and generate corrected code.

ORIGINAL REQUEST: {state['prompt']}

PREVIOUS CODE:
```python
{last_iteration.generated_code}
```

ERRORS FOUND:
{error_info}

{f'WARNINGS: {warnings_info}' if warnings_info else ''}

Please generate corrected Manim code that fixes these issues."""

    # Call LLM and track time
    start_time = time.time()
    response = await acompletion(
        model=state["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=state["max_tokens"],
        temperature=state["temperature"],
    )
    end_time = time.time()
    time_taken = end_time - start_time

    generated_code = response.choices[0].message.content.strip()

    # Extract token usage from response
    usage = response.usage if hasattr(response, 'usage') else None
    prompt_tokens = usage.prompt_tokens if usage and hasattr(usage, 'prompt_tokens') else None
    completion_tokens = usage.completion_tokens if usage and hasattr(usage, 'completion_tokens') else None
    total_tokens = usage.total_tokens if usage and hasattr(usage, 'total_tokens') else None

    # Create generation metrics
    generation_metrics = GenerationMetrics(
        time_taken=time_taken,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        model=state["model"]
    )

    # Clean up markdown formatting - be aggressive about removing code fences
    # Remove starting markers
    if generated_code.startswith("```python"):
        generated_code = generated_code[len("```python"):].strip()
    elif generated_code.startswith("```"):
        generated_code = generated_code[3:].strip()

    # Remove ending markers
    if generated_code.endswith("```"):
        generated_code = generated_code[:-3].strip()

    # Remove any remaining code fence markers in the middle or end
    lines = generated_code.split('\n')
    cleaned_lines = []
    for line in lines:
        # Skip lines that are just code fence markers
        if line.strip() in ['```', '```python', '```py']:
            continue
        cleaned_lines.append(line)

    generated_code = '\n'.join(cleaned_lines).strip()

    logger_generate.info(f"Generated {len(generated_code)} characters of code in {time_taken:.2f}s")
    if total_tokens:
        logger_generate.info(f"Token usage: {total_tokens} total ({prompt_tokens} prompt + {completion_tokens} completion)")

    return {
        "generated_code": generated_code,
        "messages": [HumanMessage(content=user_message)],
        "status": IterationStatus.VALIDATING,
        "generation_metrics": generation_metrics
    }


async def validate_code_node(state: WorkflowState) -> dict:
    """
    Node that validates the generated Manim code.
    Runs syntax checks and Manim dry-run.
    """
    # Create session-aware logger
    logger_validate = get_logger_with_session("Validate", state["session_id"])
    logger_validate.info(f"Validating code for iteration {state['current_iteration'] + 1}")

    code = state["generated_code"]

    # Track validation time
    start_time = time.time()
    validation_result = await validate_code(code, dry_run=True, session_id=state["session_id"])
    end_time = time.time()

    # Create validation metrics
    validation_metrics = ValidationMetrics(
        time_taken=end_time - start_time
    )

    # Create iteration record with metrics
    iteration = CodeIteration(
        iteration_number=state["current_iteration"] + 1,
        generated_code=code,
        validation_result=validation_result,
        timestamp=datetime.utcnow(),
        status=IterationStatus.SUCCESS if validation_result["is_valid"] else IterationStatus.REFINING,
        generation_metrics=state.get("generation_metrics"),
        validation_metrics=validation_metrics
    )

    # Add to history
    iterations_history = state["iterations_history"].copy()
    iterations_history.append(iteration)

    logger_validate.info(f"Validation result: {validation_result['is_valid']} (took {validation_metrics.time_taken:.2f}s)")
    if not validation_result["is_valid"]:
        logger_validate.warning(f"Errors: {validation_result['errors']}")

    return {
        "validation_result": validation_result,
        "iterations_history": iterations_history,
        "current_iteration": state["current_iteration"] + 1,
        "validation_metrics": validation_metrics
    }


def decide_next_step(state: WorkflowState) -> str:
    """
    Decision node that determines what to do next.
    Routes to either:
    - 'complete' if code is valid
    - 'refine' if code has errors and we haven't hit max iterations
    - 'max_iterations' if we've exhausted attempts
    """
    # Create session-aware logger
    logger_decide = get_logger_with_session("Decide", state["session_id"])

    validation = state["validation_result"]
    current_iter = state["current_iteration"]
    max_iter = state["max_iterations"]

    logger_decide.info(f"Iteration {current_iter}/{max_iter}, Valid: {validation['is_valid']}")

    if validation["is_valid"]:
        logger_decide.success("Code is valid! Going to complete.")
        return "complete"
    elif current_iter >= max_iter:
        logger_decide.warning("Max iterations reached. Stopping.")
        return "max_iterations"
    else:
        logger_decide.info("Code has errors. Going to refine.")
        return "refine"


async def complete_node(state: WorkflowState) -> dict:
    """
    Node for successful completion.
    """
    # Create session-aware logger
    logger_complete = get_logger_with_session("Complete", state["session_id"])
    logger_complete.success("Code generation successful!")
    return {
        "status": IterationStatus.SUCCESS,
        "error_message": None
    }


async def max_iterations_node(state: WorkflowState) -> dict:
    """
    Node for when max iterations is reached without success.
    """
    # Create session-aware logger
    logger_max_iter = get_logger_with_session("MaxIterations", state["session_id"])
    logger_max_iter.warning("Maximum iterations reached without valid code.")
    return {
        "status": IterationStatus.MAX_ITERATIONS_REACHED,
        "error_message": "Maximum iterations reached. Code still has validation errors."
    }


async def refine_node(state: WorkflowState) -> dict:
    """
    Node that prepares for refinement by updating status.
    The actual refinement happens in the next generate_code_node call.
    """
    # Create session-aware logger
    logger_refine = get_logger_with_session("Refine", state["session_id"])
    logger_refine.info("Preparing for refinement...")
    return {
        "status": IterationStatus.REFINING
    }


def create_workflow() -> StateGraph:
    """
    Create the LangGraph workflow for iterative code generation.

    Workflow structure:
    START -> generate -> validate -> decide
                            ^          |
                            |          v
                         refine <- [has errors?]
                                      |
                                      v
                                  complete or max_iterations -> END
    """
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("generate", generate_code_node)
    workflow.add_node("validate", validate_code_node)
    workflow.add_node("refine", refine_node)
    workflow.add_node("complete", complete_node)
    workflow.add_node("max_iterations", max_iterations_node)

    # Add edges
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", "validate")

    # Conditional edges from decide
    workflow.add_conditional_edges(
        "validate",
        decide_next_step,
        {
            "complete": "complete",
            "refine": "refine",
            "max_iterations": "max_iterations"
        }
    )

    # Refine loops back to generate
    workflow.add_edge("refine", "generate")

    # Terminal nodes
    workflow.add_edge("complete", END)
    workflow.add_edge("max_iterations", END)

    return workflow.compile()


async def run_iterative_generation(
    session_id: str,
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    max_iterations: int = 5,
    progress_callback: Optional[Callable[[dict], None]] = None
) -> WorkflowState:
    """
    Run the iterative code generation workflow.

    Args:
        session_id: Unique session identifier
        prompt: User's prompt for the animation
        model: LLM model to use
        temperature: Generation temperature
        max_tokens: Maximum tokens for generation
        max_iterations: Maximum refinement iterations
        progress_callback: Optional callback for progress updates

    Returns:
        Final workflow state with results
    """
    # Create session-aware logger
    logger = get_logger_with_session("Workflow", session_id)
    logger.info(f"Starting iterative generation")
    logger.info(f"Model: {model}, Max iterations: {max_iterations}")

    # Initialize state
    initial_state: WorkflowState = {
        "session_id": session_id,
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "max_iterations": max_iterations,
        "current_iteration": 0,
        "messages": [],
        "generated_code": None,
        "validation_result": None,
        "iterations_history": [],
        "status": IterationStatus.GENERATING,
        "error_message": None,
        "generation_metrics": None,
        "validation_metrics": None
    }

    # Create and run workflow
    workflow = create_workflow()

    # Execute workflow with streaming if callback provided
    if progress_callback:
        # Stream events from workflow
        async for event in workflow.astream(initial_state):
            # Extract node name and state from event
            if event:
                for node_name, node_state in event.items():
                    # Send progress update
                    progress_data = {
                        "session_id": session_id,
                        "node": node_name,
                        "status": node_state.get("status", IterationStatus.GENERATING),
                        "current_iteration": node_state.get("current_iteration", 0),
                        "max_iterations": max_iterations,
                        "generated_code": node_state.get("generated_code"),
                        "validation_result": node_state.get("validation_result"),
                        "iterations_history": node_state.get("iterations_history", []),
                        "error_message": node_state.get("error_message")
                    }
                    await progress_callback(progress_data)

        # Get final state
        final_state = await workflow.ainvoke(initial_state)
    else:
        # Execute workflow normally without streaming
        final_state = await workflow.ainvoke(initial_state)

    logger.success(f"Completed with status: {final_state['status']}")
    logger.info(f"Total iterations: {final_state['current_iteration']}")

    return final_state


async def run_iterative_generation_streaming(
    session_id: str,
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    max_iterations: int = 5
):
    """
    Run the iterative code generation workflow with streaming.
    Yields progress updates as the workflow executes.

    Args:
        session_id: Unique session identifier
        prompt: User's prompt for the animation
        model: LLM model to use
        temperature: Generation temperature
        max_tokens: Maximum tokens for generation
        max_iterations: Maximum refinement iterations

    Yields:
        Progress updates as dictionaries
    """
    # Create session-aware logger
    logger = get_logger_with_session("Workflow", session_id)
    logger.info(f"[Streaming] Starting iterative generation")
    logger.info(f"[Streaming] Model: {model}, Max iterations: {max_iterations}")

    # Initialize state
    initial_state: WorkflowState = {
        "session_id": session_id,
        "prompt": prompt,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "max_iterations": max_iterations,
        "current_iteration": 0,
        "messages": [],
        "generated_code": None,
        "validation_result": None,
        "iterations_history": [],
        "status": IterationStatus.GENERATING,
        "error_message": None,
        "generation_metrics": None,
        "validation_metrics": None
    }

    # Create workflow
    workflow = create_workflow()

    # Yield initial status
    yield {
        "session_id": session_id,
        "event": "start",
        "status": IterationStatus.GENERATING,
        "current_iteration": 0,
        "max_iterations": max_iterations,
        "message": "Starting code generation workflow..."
    }

    # Stream workflow execution
    final_state = None
    async for event in workflow.astream(initial_state):
        if event:
            for node_name, node_state in event.items():
                # Extract iteration info if available
                iterations_history = node_state.get("iterations_history", [])
                current_iteration = node_state.get("current_iteration", 0)

                # Send progress update with full iteration details
                progress_data = {
                    "session_id": session_id,
                    "event": "progress",
                    "node": node_name,
                    "status": node_state.get("status", IterationStatus.GENERATING),
                    "current_iteration": current_iteration,
                    "max_iterations": max_iterations,
                    "generated_code": node_state.get("generated_code"),
                    "validation_result": node_state.get("validation_result"),
                    "iterations_history": [
                        {
                            "iteration_number": iter.iteration_number,
                            "generated_code": iter.generated_code,
                            "validation_result": iter.validation_result,
                            "timestamp": iter.timestamp.isoformat(),
                            "status": iter.status,
                            "generation_metrics": {
                                "time_taken": iter.generation_metrics.time_taken,
                                "prompt_tokens": iter.generation_metrics.prompt_tokens,
                                "completion_tokens": iter.generation_metrics.completion_tokens,
                                "total_tokens": iter.generation_metrics.total_tokens,
                                "model": iter.generation_metrics.model
                            } if iter.generation_metrics else None,
                            "validation_metrics": {
                                "time_taken": iter.validation_metrics.time_taken
                            } if iter.validation_metrics else None
                        }
                        for iter in iterations_history
                    ],
                    "error_message": node_state.get("error_message"),
                    "message": f"Node '{node_name}' completed for iteration {current_iteration}"
                }
                yield progress_data

                # Keep track of the most complete state (preserve data from validate node)
                if final_state is None:
                    final_state = node_state
                else:
                    # Merge states, preserving non-None values
                    final_state = {**final_state, **{k: v for k, v in node_state.items() if v is not None}}

    # Yield final completion event
    if final_state:
        yield {
            "session_id": session_id,
            "event": "complete",
            "status": final_state.get("status", IterationStatus.SUCCESS),
            "current_iteration": final_state.get("current_iteration", 0),
            "max_iterations": max_iterations,
            "generated_code": final_state.get("generated_code"),
            "validation_result": final_state.get("validation_result"),
            "iterations_history": [
                {
                    "iteration_number": iter.iteration_number,
                    "generated_code": iter.generated_code,
                    "validation_result": iter.validation_result,
                    "timestamp": iter.timestamp.isoformat(),
                    "status": iter.status,
                    "generation_metrics": {
                        "time_taken": iter.generation_metrics.time_taken,
                        "prompt_tokens": iter.generation_metrics.prompt_tokens,
                        "completion_tokens": iter.generation_metrics.completion_tokens,
                        "total_tokens": iter.generation_metrics.total_tokens,
                        "model": iter.generation_metrics.model
                    } if iter.generation_metrics else None,
                    "validation_metrics": {
                        "time_taken": iter.validation_metrics.time_taken
                    } if iter.validation_metrics else None
                }
                for iter in final_state.get("iterations_history", [])
            ],
            "message": "Workflow completed successfully!"
        }

    logger.success(f"[Streaming] Completed with status: {final_state.get('status') if final_state else 'unknown'}")
    logger.info(f"[Streaming] Total iterations: {final_state.get('current_iteration', 0) if final_state else 0}")
