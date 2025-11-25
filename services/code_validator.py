"""
Code validation service for Manim code.
Validates syntax and runs Manim dry-run to catch errors.
"""
import ast
import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional

from utils.logger import get_logger


logger = get_logger("CodeValidator")

class ValidationResult:
    """Result of code validation."""
    def __init__(self):
        self.is_valid: bool = False
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.error_details: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_details": self.error_details
        }


async def validate_python_syntax(code: str) -> ValidationResult:
    """
    Validate Python syntax of the generated code.

    Args:
        code: Python code to validate

    Returns:
        ValidationResult with syntax validation results
    """
    result = ValidationResult()

    try:
        ast.parse(code)
        result.is_valid = True
    except SyntaxError as e:
        result.is_valid = False
        result.errors.append(f"Syntax Error at line {e.lineno}: {e.msg}")
        result.error_details = str(e)
    except Exception as e:
        result.is_valid = False
        result.errors.append(f"Parse Error: {str(e)}")
        result.error_details = str(e)

    return result


async def validate_manim_imports(code: str) -> ValidationResult:
    """
    Check if code has proper Manim imports.

    Args:
        code: Python code to validate

    Returns:
        ValidationResult with import validation results
    """
    result = ValidationResult()

    if "from manim import" not in code and "import manim" not in code:
        result.warnings.append("Code may be missing Manim imports")

    result.is_valid = True
    return result


async def validate_manim_structure(code: str) -> ValidationResult:
    """
    Check if code has proper Manim scene structure.

    Args:
        code: Python code to validate

    Returns:
        ValidationResult with structure validation results
    """
    result = ValidationResult()

    if "class GeneratedScene" not in code:
        result.errors.append("Code must contain a 'GeneratedScene' class")
        result.is_valid = False
        return result

    if "def construct(self)" not in code:
        result.errors.append("GeneratedScene must have a 'construct' method")
        result.is_valid = False
        return result

    result.is_valid = True
    return result


async def validate_manim_dry_run(
    code: str,
    progress_callback: Optional[Callable[[str, str], None]] = None,
    timeout: int = 600  # 10 minutes default timeout
) -> ValidationResult:
    """
    Run Manim with --dry_run flag to validate without rendering.
    This catches runtime errors like missing attributes, invalid animations, etc.

    Args:
        code: Python code to validate
        progress_callback: Optional callback function(stage, message) for progress updates
        timeout: Maximum time in seconds to wait for validation (default: 180)

    Returns:
        ValidationResult with dry-run validation results
    """
    result = ValidationResult()
    temp_dir = None
    process = None

    def emit_progress(stage: str, message: str):
        """Helper to emit progress if callback is provided."""
        if progress_callback:
            progress_callback(stage, message)

    try:
        emit_progress("setup", "Creating temporary validation environment")

        # Create temporary directory for validation
        temp_dir = tempfile.mkdtemp(prefix="manim_validate_")
        script_path = Path(temp_dir) / "validate_scene.py"

        # Use the main project's media directory to reuse TeX cache
        # This significantly speeds up validation by avoiding recompilation of cached TeX
        project_root = Path.cwd()
        media_dir = project_root / "media"

        # Create media directories if they don't exist
        media_dir.mkdir(exist_ok=True)
        (media_dir / "Tex").mkdir(exist_ok=True)
        (media_dir / "images").mkdir(exist_ok=True)
        (media_dir / "text").mkdir(exist_ok=True)
        (media_dir / "videos").mkdir(exist_ok=True)

        # Write code to file
        with open(script_path, "w") as f:
            f.write(code)

        emit_progress("validation", "Starting Manim dry-run validation")

        # Run manim with --dry_run flag and additional flags for better output
        # Use --media_dir to point to the main project's media directory for TeX cache reuse
        cmd = [
            sys.executable, "-m", "manim",
            "--dry_run",
            "--verbosity", "INFO",
            "--progress_bar", "display",
            "--media_dir", str(media_dir),
            str(script_path),
            "GeneratedScene"
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=project_root
        )

        # Stream output in real-time
        stdout_lines = []
        stderr_lines = []

        async def read_stream(stream, is_stderr=False):
            """Read stream line by line and emit progress."""
            lines = stderr_lines if is_stderr else stdout_lines
            stream_name = "stderr" if is_stderr else "stdout"

            while True:
                line = await stream.readline()
                if not line:
                    break

                decoded_line = line.decode().rstrip()
                lines.append(decoded_line)

                # Emit progress for important lines
                if decoded_line:
                    logger.debug(decoded_line)

        # Read both streams concurrently with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(
                    read_stream(process.stdout, is_stderr=False),
                    read_stream(process.stderr, is_stderr=True)
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Validation process exceeded timeout of {timeout}s")
            result.is_valid = False
            result.errors.append(f"Validation timeout after {timeout} seconds")
            emit_progress("timeout", f"Validation timeout after {timeout} seconds")
            return result

        # Wait for process to complete
        await process.wait()

        stdout_str = "\n".join(stdout_lines)
        stderr_str = "\n".join(stderr_lines)

        if process.returncode != 0:
            result.is_valid = False
            emit_progress("failed", "Manim validation failed")

            # Extract meaningful error messages
            for line in stderr_lines:
                if "Error" in line or "Exception" in line or "Traceback" in line:
                    result.errors.append(line.strip())

            # If no specific errors found, add full stderr
            if not result.errors:
                result.errors.append("Manim validation failed")

            result.error_details = f"STDOUT:\n{stdout_str}\n\nSTDERR:\n{stderr_str}"
        else:
            result.is_valid = True
            emit_progress("completed", "Manim validation successful")

    except asyncio.CancelledError:
        # Handle cancellation gracefully
        logger.warning("Validation task was cancelled")
        result.is_valid = False
        result.errors.append("Validation was cancelled")
        emit_progress("cancelled", "Validation was cancelled")
        raise  # Re-raise to allow proper cleanup

    except Exception as e:
        result.is_valid = False
        result.errors.append(f"Validation error: {str(e)}")
        result.error_details = str(e)
        emit_progress("error", f"Validation error: {str(e)}")

    finally:
        # Ensure subprocess is terminated
        if process and process.returncode is None:
            try:
                logger.info("Terminating validation subprocess...")
                process.terminate()
                try:
                    # Wait briefly for graceful termination
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if it doesn't terminate gracefully
                    logger.warning("Force killing validation subprocess...")
                    process.kill()
                    await process.wait()
            except Exception as cleanup_error:
                logger.error(f"Error during subprocess cleanup: {cleanup_error}")

        # Clean up temp directory
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            emit_progress("cleanup", "Cleaned up temporary files")

    return result


async def validate_code(
    code: str,
    dry_run: bool = True,
    progress_callback: Optional[Callable[[str, str], None]] = None
) -> Dict:
    """
    Comprehensive code validation combining all checks.

    Args:
        code: Python code to validate
        dry_run: Whether to run Manim dry-run validation (slower but more thorough)
        progress_callback: Optional callback function(stage, message) for progress updates

    Returns:
        Dictionary with validation results
    """
    all_errors = []
    all_warnings = []
    error_details = []

    def emit_progress(stage: str, message: str):
        """Helper to emit progress if callback is provided."""
        if progress_callback:
            progress_callback(stage, message)

    # Step 1: Syntax validation
    emit_progress("syntax", "Validating Python syntax")
    syntax_result = await validate_python_syntax(code)
    all_errors.extend(syntax_result.errors)
    all_warnings.extend(syntax_result.warnings)
    if syntax_result.error_details:
        error_details.append(f"Syntax Validation:\n{syntax_result.error_details}")

    # If syntax is invalid, stop here
    if not syntax_result.is_valid:
        emit_progress("failed", "Syntax validation failed")
        return {
            "is_valid": False,
            "errors": all_errors,
            "warnings": all_warnings,
            "error_details": "\n\n".join(error_details) if error_details else None
        }

    emit_progress("syntax", "Syntax validation passed")

    # Step 2: Import validation
    emit_progress("imports", "Checking Manim imports")
    import_result = await validate_manim_imports(code)
    all_warnings.extend(import_result.warnings)
    emit_progress("imports", "Import validation completed")

    # Step 3: Structure validation
    emit_progress("structure", "Validating Manim scene structure")
    structure_result = await validate_manim_structure(code)
    all_errors.extend(structure_result.errors)
    all_warnings.extend(structure_result.warnings)

    if not structure_result.is_valid:
        emit_progress("failed", "Structure validation failed")
        return {
            "is_valid": False,
            "errors": all_errors,
            "warnings": all_warnings,
            "error_details": "\n\n".join(error_details) if error_details else None
        }

    emit_progress("structure", "Structure validation passed")

    # Step 4: Dry-run validation (optional, more thorough)
    if dry_run:
        emit_progress("dry_run", "Starting Manim dry-run validation")
        dry_run_result = await validate_manim_dry_run(code, progress_callback)
        all_errors.extend(dry_run_result.errors)
        all_warnings.extend(dry_run_result.warnings)
        if dry_run_result.error_details:
            error_details.append(f"Manim Dry-Run:\n{dry_run_result.error_details}")

        if not dry_run_result.is_valid:
            emit_progress("failed", "Dry-run validation failed")
            return {
                "is_valid": False,
                "errors": all_errors,
                "warnings": all_warnings,
                "error_details": "\n\n".join(error_details) if error_details else None
            }

    # All validations passed
    emit_progress("completed", "All validations passed successfully")
    return {
        "is_valid": True,
        "errors": all_errors,
        "warnings": all_warnings,
        "error_details": None
    }
