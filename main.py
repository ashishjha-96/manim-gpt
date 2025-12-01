from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import litellm
from dotenv import load_dotenv
import os
from pathlib import Path

from api import model_router, session_router
from utils.logger import get_logger, setup_logging

# Load environment variables from .env file
load_dotenv()

# Setup logging to intercept standard logging and redirect to loguru
setup_logging()

# Create logger
logger = get_logger("Main")

# Configure LiteLLM logging
# Set to DEBUG for verbose logging, or leave as INFO for cleaner output
litellm_log_level = os.getenv("LITELLM_LOG_LEVEL", "INFO")
os.environ['LITELLM_LOG'] = litellm_log_level

# Disable the deprecated set_verbose (we use LITELLM_LOG env var instead)
litellm.set_verbose = False

logger.info(f"LiteLLM logging level set to: {litellm_log_level}")

app = FastAPI(title="Manim GPT - AI-Powered Video Generation API")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers - MUST come before static file serving
app.include_router(model_router)
app.include_router(session_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Mount static files for production frontend
# Check if frontend/dist exists (production build)
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    logger.info(f"Frontend dist directory found at {frontend_dist}")

    # Mount static assets (JS, CSS, images) from the assets subdirectory
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        logger.info(f"Mounted static assets from {assets_dir}")

    # Catch-all route for SPA - MUST be defined LAST
    # This serves index.html for all frontend routes (React Router handles client-side routing)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Don't interfere with API routes (let them return 404 if not found)
        if full_path.startswith(("api/", "session/", "models/", "health")):
            # This will naturally 404 if the route doesn't exist
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")

        # Serve index.html for all other routes (frontend SPA)
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Frontend not built")
else:
    logger.warning(f"Frontend dist directory not found at {frontend_dist}")
    logger.warning("Running in API-only mode. Frontend will not be served.")

    # Fallback root endpoint when frontend is not available
    @app.get("/")
    async def root():
        return {
            "message": "Manim GPT - AI-Powered Video Generation API",
            "status": "running",
            "mode": "api-only",
            "endpoints": {
                "iterative_generate": "/session/generate",
                "session_status": "/session/status/{session_id}",
                "render_session": "/session/render (async)",
                "render_status": "/session/render-status/{session_id}",
                "download_session_video": "/session/download",
                "list_sessions": "/session/list",
                "list_providers": "/models/providers",
                "list_models_by_provider": "/models/providers/{provider}",
                "health": "/health"
            }
        }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Manim GPT API server on http://0.0.0.0:8000")
    # Use log_config=None to disable uvicorn's default logging and use our intercepted logging
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
