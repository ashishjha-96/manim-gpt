"""
Centralized logging configuration using loguru.
"""
import sys
from loguru import logger

# Remove default handler
logger.remove()

# Add custom handler with nice formatting
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[context]: <20}</cyan> | <level>{message}</level>",
    level="INFO",
    colorize=True,
)

def get_logger(context: str):
    """
    Get a logger with a specific context.

    Args:
        context: The context/component name (e.g., "API", "Workflow", "Generate")

    Returns:
        Logger instance bound with the context
    """
    return logger.bind(context=context)
