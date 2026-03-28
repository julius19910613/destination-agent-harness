from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
import os

# Load environment variables from .env file
# Use explicit path to ensure .env is loaded from project root
env_path = Path(__file__).parent / ".env"
print(f"Loading .env from: {env_path}")
print(f".env exists: {env_path.exists()}")
load_dotenv(dotenv_path=env_path)
print(f"GOOGLE_API_KEY after load: {os.getenv('GOOGLE_API_KEY', 'NOT FOUND')}")

from app.api.routes import router as api_router

app = FastAPI(
    title="Destination Extraction API",
    description="AI-powered destination extraction from natural language using Google Gemini",
    version="1.0.0",
)


class HealthResponse(BaseModel):
    status: str
    version: str


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to Destination Extraction API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return HealthResponse(status="ok", version="1.0.0")


# Register API routes
app.include_router(api_router)

# Register monitoring routes
from app.api.routes_metrics import router as metrics_router
app.include_router(metrics_router)

# Register advanced destination routes (Phase 3)
from app.api.routes_advanced import router as advanced_router
app.include_router(advanced_router)

# Register session/context routes (Phase 4)
from app.api.routes_session import router as session_router
app.include_router(session_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
