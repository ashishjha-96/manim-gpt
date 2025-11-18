"""
Structured logging configuration for Manim-GPT application.

This module provides structured JSON logging with contextual information,
making logs easier to parse, search, and analyze.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import os
from contextvars import ContextVar

# Context variables for request-scoped logging context
log_context: ContextVar[Dict[str, Any]] = ContextVar('log_context', default={})


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in structured JSON format.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with structured fields."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add context from context variables
        context = log_context.get()
        if context:
            log_data['context'] = context

        # Add extra fields if present
        if hasattr(record, 'session_id') and record.session_id:
            log_data['session_id'] = record.session_id

        if hasattr(record, 'node') and record.node:
            log_data['node'] = record.node

        if hasattr(record, 'iteration') and record.iteration is not None:
            log_data['iteration'] = record.iteration

        if hasattr(record, 'status') and record.status:
            log_data['status'] = record.status

        if hasattr(record, 'model') and record.model:
            log_data['model'] = record.model

        if hasattr(record, 'max_iterations') and record.max_iterations is not None:
            log_data['max_iterations'] = record.max_iterations

        if hasattr(record, 'code_length') and record.code_length is not None:
            log_data['code_length'] = record.code_length

        if hasattr(record, 'valid') and record.valid is not None:
            log_data['valid'] = record.valid

        if hasattr(record, 'errors') and record.errors:
            log_data['errors'] = record.errors

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add location information
        log_data['location'] = {
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName
        }

        return json.dumps(log_data, default=str)


class HumanReadableFormatter(logging.Formatter):
    """
    Formatter that outputs logs in a human-readable format for development.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record in human-readable format."""
        timestamp = datetime.utcnow().strftime('%H:%M:%S')

        # Build the base message
        parts = [f"{timestamp} [{record.levelname}] [{record.name}]"]

        # Add context information if present
        if hasattr(record, 'session_id') and record.session_id:
            parts.append(f"[Session: {record.session_id[:8]}]")

        if hasattr(record, 'node') and record.node:
            parts.append(f"[{record.node}]")

        if hasattr(record, 'iteration') and record.iteration is not None:
            parts.append(f"[Iter: {record.iteration}]")

        # Add the actual message
        parts.append(record.getMessage())

        message = " ".join(parts)

        # Add exception if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)

        return message


def setup_logging(
    log_level: str = "INFO",
    log_format: str = "human",  # "json" or "human"
    log_file: Optional[str] = None
) -> None:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format ("json" for structured, "human" for readable)
        log_file: Optional file path to write logs to
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Choose formatter based on format setting
    if log_format.lower() == "json":
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(StructuredFormatter())  # Always use JSON for file logs
        root_logger.addHandler(file_handler)

    # Configure uvicorn loggers
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.propagate = True

    # Configure LiteLLM logger
    litellm_logger = logging.getLogger("LiteLLM")
    litellm_logger.setLevel(logging.WARNING)  # Reduce LiteLLM noise

    logging.info("Structured logging initialized", extra={
        'log_level': log_level,
        'log_format': log_format,
        'log_file': log_file
    })


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_log_context(**kwargs) -> None:
    """
    Set contextual information for logging (e.g., session_id).
    This context will be included in all subsequent log messages in this context.

    Args:
        **kwargs: Key-value pairs to add to log context
    """
    current_context = log_context.get().copy()
    current_context.update(kwargs)
    log_context.set(current_context)


def clear_log_context() -> None:
    """Clear the logging context."""
    log_context.set({})


def get_log_context() -> Dict[str, Any]:
    """Get the current logging context."""
    return log_context.get().copy()


# Logger adapter for convenience methods
class StructuredLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that makes it easy to add structured context to logs.
    """

    def process(self, msg, kwargs):
        """Add extra context to log records."""
        extra = kwargs.get('extra', {})

        # Merge with adapter's context
        if self.extra:
            extra.update(self.extra)

        kwargs['extra'] = extra
        return msg, kwargs


def get_structured_logger(
    name: str,
    session_id: Optional[str] = None,
    node: Optional[str] = None,
    **context
) -> StructuredLoggerAdapter:
    """
    Get a structured logger with predefined context.

    Args:
        name: Logger name
        session_id: Optional session ID to include in logs
        node: Optional node name (for workflow logging)
        **context: Additional context to include

    Returns:
        StructuredLoggerAdapter instance
    """
    logger = logging.getLogger(name)

    extra = {}
    if session_id:
        extra['session_id'] = session_id
    if node:
        extra['node'] = node
    extra.update(context)

    return StructuredLoggerAdapter(logger, extra)


# Initialize logging from environment variables if running as main module
def init_from_env() -> None:
    """Initialize logging configuration from environment variables."""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_format = os.getenv('LOG_FORMAT', 'human')
    log_file = os.getenv('LOG_FILE')

    setup_logging(log_level=log_level, log_format=log_format, log_file=log_file)
