"""
LangGraph workflow for iterative Manim code generation and refinement.
"""
from typing import TypedDict, Annotated, Sequence, Callable, Optional, Any
from datetime import datetime
import operator
import asyncio

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from litellm import acompletion
from services.code_validator import validate_code
from models.session import IterationStatus, CodeIteration
from utils.logging import get_logger

# Initialize logger
logger = get_logger(__name__)


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


async def generate_code_node(state: WorkflowState) -> dict:
    """
    Node that generates Manim code using LLM.
    For first iteration, uses the original prompt.
    For refinements, includes error feedback.
    """
    logger.info(
        "Starting code generation",
        extra={
            'node': 'Generate',
            'session_id': state['session_id'],
            'iteration': state['current_iteration'] + 1,
            'max_iterations': state['max_iterations']
        }
    )

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

    # Call LLM
    response = await acompletion(
        model=state["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        max_tokens=state["max_tokens"],
        temperature=state["temperature"],
    )

    generated_code = response.choices[0].message.content.strip()

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

    logger.info(
        "Code generation completed",
        extra={
            'node': 'Generate',
            'session_id': state['session_id'],
            'iteration': state['current_iteration'] + 1,
            'code_length': len(generated_code),
            'model': state['model']
        }
    )

    return {
        "generated_code": generated_code,
        "messages": [HumanMessage(content=user_message)],
        "status": IterationStatus.VALIDATING
    }


async def validate_code_node(state: WorkflowState) -> dict:
    """
    Node that validates the generated Manim code.
    Runs syntax checks and Manim dry-run.
    """
    logger.info(
        "Starting code validation",
        extra={
            'node': 'Validate',
            'session_id': state['session_id'],
            'iteration': state['current_iteration'] + 1
        }
    )

    code = state["generated_code"]
    validation_result = await validate_code(code, dry_run=True)

    # Create iteration record
    iteration = CodeIteration(
        iteration_number=state["current_iteration"] + 1,
        generated_code=code,
        validation_result=validation_result,
        timestamp=datetime.utcnow(),
        status=IterationStatus.SUCCESS if validation_result["is_valid"] else IterationStatus.REFINING
    )

    # Add to history
    iterations_history = state["iterations_history"].copy()
    iterations_history.append(iteration)

    if validation_result["is_valid"]:
        logger.info(
            "Code validation successful",
            extra={
                'node': 'Validate',
                'session_id': state['session_id'],
                'iteration': state['current_iteration'] + 1,
                'valid': True
            }
        )
    else:
        logger.warning(
            "Code validation failed",
            extra={
                'node': 'Validate',
                'session_id': state['session_id'],
                'iteration': state['current_iteration'] + 1,
                'valid': False,
                'errors': validation_result.get('errors', [])
            }
        )

    return {
        "validation_result": validation_result,
        "iterations_history": iterations_history,
        "current_iteration": state["current_iteration"] + 1,
    }


def decide_next_step(state: WorkflowState) -> str:
    """
    Decision node that determines what to do next.
    Routes to either:
    - 'complete' if code is valid
    - 'refine' if code has errors and we haven't hit max iterations
    - 'max_iterations' if we've exhausted attempts
    """
    validation = state["validation_result"]
    current_iter = state["current_iteration"]
    max_iter = state["max_iterations"]

    logger.info(
        "Making routing decision",
        extra={
            'node': 'Decide',
            'session_id': state['session_id'],
            'iteration': current_iter,
            'max_iterations': max_iter,
            'valid': validation['is_valid']
        }
    )

    if validation["is_valid"]:
        logger.info(
            "Routing to complete - code is valid",
            extra={
                'node': 'Decide',
                'session_id': state['session_id'],
                'status': 'complete'
            }
        )
        return "complete"
    elif current_iter >= max_iter:
        logger.warning(
            "Routing to max_iterations - limit reached",
            extra={
                'node': 'Decide',
                'session_id': state['session_id'],
                'status': 'max_iterations',
                'iteration': current_iter,
                'max_iterations': max_iter
            }
        )
        return "max_iterations"
    else:
        logger.info(
            "Routing to refine - code has errors",
            extra={
                'node': 'Decide',
                'session_id': state['session_id'],
                'status': 'refine',
                'iteration': current_iter
            }
        )
        return "refine"


async def complete_node(state: WorkflowState) -> dict:
    """
    Node for successful completion.
    """
    logger.info(
        "Code generation completed successfully",
        extra={
            'node': 'Complete',
            'session_id': state['session_id'],
            'status': 'SUCCESS',
            'iteration': state['current_iteration']
        }
    )
    return {
        "status": IterationStatus.SUCCESS,
        "error_message": None
    }


async def max_iterations_node(state: WorkflowState) -> dict:
    """
    Node for when max iterations is reached without success.
    """
    logger.warning(
        "Maximum iterations reached without valid code",
        extra={
            'node': 'MaxIterations',
            'session_id': state['session_id'],
            'status': 'MAX_ITERATIONS_REACHED',
            'iteration': state['current_iteration'],
            'max_iterations': state['max_iterations']
        }
    )
    return {
        "status": IterationStatus.MAX_ITERATIONS_REACHED,
        "error_message": "Maximum iterations reached. Code still has validation errors."
    }


async def refine_node(state: WorkflowState) -> dict:
    """
    Node that prepares for refinement by updating status.
    The actual refinement happens in the next generate_code_node call.
    """
    logger.info(
        "Preparing for code refinement",
        extra={
            'node': 'Refine',
            'session_id': state['session_id'],
            'status': 'REFINING',
            'iteration': state['current_iteration']
        }
    )
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
    logger.info(
        "Starting iterative workflow",
        extra={
            'session_id': session_id,
            'model': model,
            'max_iterations': max_iterations,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
    )

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
        "error_message": None
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

    logger.info(
        "Workflow completed",
        extra={
            'session_id': session_id,
            'status': str(final_state['status']),
            'iteration': final_state['current_iteration'],
            'max_iterations': max_iterations
        }
    )

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
    logger.info(
        "Starting streaming workflow",
        extra={
            'session_id': session_id,
            'model': model,
            'max_iterations': max_iterations,
            'temperature': temperature,
            'max_tokens': max_tokens
        }
    )

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
        "error_message": None
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
                            "status": iter.status
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
                    "status": iter.status
                }
                for iter in final_state.get("iterations_history", [])
            ],
            "message": "Workflow completed successfully!"
        }

    logger.info(
        "Streaming workflow completed",
        extra={
            'session_id': session_id,
            'status': str(final_state.get('status')) if final_state else 'unknown',
            'iteration': final_state.get('current_iteration', 0) if final_state else 0,
            'max_iterations': max_iterations
        }
    )
