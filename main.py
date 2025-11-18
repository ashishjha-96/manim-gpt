from fastapi import FastAPI
import litellm
from dotenv import load_dotenv
import os
import logging

from api import code_router, video_router, model_router, session_router
from utils.logging import setup_logging, get_logger

# Load environment variables from .env file
load_dotenv()

# Initialize structured logging
log_level = os.getenv("LOG_LEVEL", "INFO")
log_format = os.getenv("LOG_FORMAT", "human")  # "json" or "human"
log_file = os.getenv("LOG_FILE")

setup_logging(log_level=log_level, log_format=log_format, log_file=log_file)
logger = get_logger(__name__)

# Configure LiteLLM logging - reduce verbosity
litellm_log_level = os.getenv("LITELLM_LOG_LEVEL", "WARNING")
litellm_logger = logging.getLogger("LiteLLM")
litellm_logger.setLevel(getattr(logging, litellm_log_level.upper()))

# Only set verbose for debugging purposes
if log_level.upper() == "DEBUG":
    litellm.set_verbose = True
    os.environ['LITELLM_LOG'] = 'DEBUG'
else:
    litellm.set_verbose = False

logger.info(
    "Starting Manim GPT API",
    extra={
        'log_level': log_level,
        'log_format': log_format,
        'litellm_log_level': litellm_log_level
    }
)

app = FastAPI(title="Manim GPT - AI-Powered Video Generation API")

# Include routers
app.include_router(code_router)
app.include_router(video_router)
app.include_router(model_router)
app.include_router(session_router)


@app.get("/")
async def root():
    return {
        "message": "Manim GPT - AI-Powered Video Generation API",
        "status": "running",
        "endpoints": {
            "generate_video": "/video/generate",
            "download_video": "/video/download",
            "generate_code": "/code/generate",
            "generate_manim_code": "/code/generate-manim",
            "iterative_generate": "/session/generate",
            "session_status": "/session/status/{session_id}",
            "render_session": "/session/render",
            "download_session_video": "/session/download",
            "list_sessions": "/session/list",
            "list_providers": "/models/providers",
            "list_models_by_provider": "/models/providers/{provider}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    # Configure uvicorn logging to use our structured logger
    uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
    uvicorn_log_config["formatters"]["default"]["fmt"] = "%(asctime)s [%(levelname)s] [uvicorn] %(message)s"
    uvicorn_log_config["formatters"]["access"]["fmt"] = '%(asctime)s [%(levelname)s] [uvicorn.access] %(client_addr)s - "%(request_line)s" %(status_code)s'

    logger.info("Starting uvicorn server", extra={'host': '0.0.0.0', 'port': 8000})

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=uvicorn_log_config if log_format == "human" else None,
        log_level=log_level.lower()
    )
