"""
Code validation service for Manim code.
Validates syntax and runs Manim dry-run to catch errors.
"""
import ast
import asyncio
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional


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


async def validate_manim_dry_run(code: str) -> ValidationResult:
    """
    Run Manim with --dry_run flag to validate without rendering.
    This catches runtime errors like missing attributes, invalid animations, etc.

    Args:
        code: Python code to validate

    Returns:
        ValidationResult with dry-run validation results
    """
    result = ValidationResult()
    temp_dir = None

    try:
        # Create temporary directory for validation
        temp_dir = tempfile.mkdtemp(prefix="manim_validate_")
        script_path = Path(temp_dir) / "validate_scene.py"

        # Write code to file
        with open(script_path, "w") as f:
            f.write(code)

        # Run manim with --dry_run flag
        cmd = [
            sys.executable, "-m", "manim",
            "--dry_run",
            str(script_path),
            "GeneratedScene"
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=temp_dir
        )

        stdout, stderr = await process.communicate()
        stdout_str = stdout.decode() if stdout else ""
        stderr_str = stderr.decode() if stderr else ""

        if process.returncode != 0:
            result.is_valid = False

            # Parse error messages from stderr
            error_lines = stderr_str.split('\n')

            # Extract meaningful error messages
            for line in error_lines:
                if "Error" in line or "Exception" in line or "Traceback" in line:
                    result.errors.append(line.strip())

            # If no specific errors found, add full stderr
            if not result.errors:
                result.errors.append("Manim validation failed")

            result.error_details = f"STDOUT:\n{stdout_str}\n\nSTDERR:\n{stderr_str}"
        else:
            result.is_valid = True

    except Exception as e:
        result.is_valid = False
        result.errors.append(f"Validation error: {str(e)}")
        result.error_details = str(e)

    finally:
        # Clean up temp directory
        if temp_dir:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    return result


async def validate_code(code: str, dry_run: bool = True) -> Dict:
    """
    Comprehensive code validation combining all checks.

    Args:
        code: Python code to validate
        dry_run: Whether to run Manim dry-run validation (slower but more thorough)

    Returns:
        Dictionary with validation results
    """
    all_errors = []
    all_warnings = []
    error_details = []

    # Step 1: Syntax validation
    syntax_result = await validate_python_syntax(code)
    all_errors.extend(syntax_result.errors)
    all_warnings.extend(syntax_result.warnings)
    if syntax_result.error_details:
        error_details.append(f"Syntax Validation:\n{syntax_result.error_details}")

    # If syntax is invalid, stop here
    if not syntax_result.is_valid:
        return {
            "is_valid": False,
            "errors": all_errors,
            "warnings": all_warnings,
            "error_details": "\n\n".join(error_details) if error_details else None
        }

    # Step 2: Import validation
    import_result = await validate_manim_imports(code)
    all_warnings.extend(import_result.warnings)

    # Step 3: Structure validation
    structure_result = await validate_manim_structure(code)
    all_errors.extend(structure_result.errors)
    all_warnings.extend(structure_result.warnings)

    if not structure_result.is_valid:
        return {
            "is_valid": False,
            "errors": all_errors,
            "warnings": all_warnings,
            "error_details": "\n\n".join(error_details) if error_details else None
        }

    # Step 4: Dry-run validation (optional, more thorough)
    if dry_run:
        dry_run_result = await validate_manim_dry_run(code)
        all_errors.extend(dry_run_result.errors)
        all_warnings.extend(dry_run_result.warnings)
        if dry_run_result.error_details:
            error_details.append(f"Manim Dry-Run:\n{dry_run_result.error_details}")

        if not dry_run_result.is_valid:
            return {
                "is_valid": False,
                "errors": all_errors,
                "warnings": all_warnings,
                "error_details": "\n\n".join(error_details) if error_details else None
            }

    # All validations passed
    return {
        "is_valid": True,
        "errors": all_errors,
        "warnings": all_warnings,
        "error_details": None
    }
