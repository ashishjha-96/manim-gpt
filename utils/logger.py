"""
Centralized logging configuration using loguru.
"""
import sys
import logging
from loguru import logger

# Remove default handler
logger.remove()

# Add custom handler with nice formatting
# Format includes optional session_id for traceability
def format_record(record):
    """Custom formatter that includes session_id if available."""
    session_id = record["extra"].get("session_id", "")
    if session_id:
        # Show only first 8 chars of session_id for readability
        session_prefix = f"[{session_id[:8]}] "
    else:
        session_prefix = ""

    return (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[context]: <20}</cyan> | "
        f"<yellow>{session_prefix}</yellow>"
        "<level>{message}</level>\n"
    )

logger.add(
    sys.stderr,
    format=format_record,
    level="INFO",
    colorize=True,
)


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages and redirect them to loguru.
    This is useful for integrating third-party libraries (like uvicorn) with loguru.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # Extract context from logger name (e.g., "uvicorn.access" -> "uvicorn.access")
        context = record.name

        logger.opt(depth=depth, exception=record.exc_info).bind(context=context).log(
            level, record.getMessage()
        )


def setup_logging():
    """
    Setup logging by intercepting standard Python logging and redirecting to loguru.
    This should be called early in the application startup.
    """
    # Intercept everything at the root logger
    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel("INFO")

    # Remove every other logger's handlers and propagate to root logger
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


def get_logger(context: str):
    """
    Get a logger with a specific context.

    Args:
        context: The context/component name (e.g., "API", "Workflow", "Generate")

    Returns:
        Logger instance bound with the context
    """
    return logger.bind(context=context)


def get_logger_with_session(context: str, session_id: str):
    """
    Get a logger with a specific context and session ID.

    Args:
        context: The context/component name (e.g., "API", "Workflow", "Generate")
        session_id: The session UUID for traceability

    Returns:
        Logger instance bound with the context and session_id
    """
    return logger.bind(context=context, session_id=session_id)
