"""
FastAPI application entrypoint for the Mini App backend.
"""
from api.main import app
from config.settings import settings


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
