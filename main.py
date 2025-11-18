from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import litellm
from dotenv import load_dotenv

from api import code_router, video_router, model_router, session_router

# Load environment variables from .env file
load_dotenv()

# Enable LiteLLM debug mode
litellm.set_verbose = True

app = FastAPI(title="Manim GPT - AI-Powered Video Generation API")

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
