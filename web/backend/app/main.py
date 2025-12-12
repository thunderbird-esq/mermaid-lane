"""
IPTV Web Application - FastAPI Backend

A secure, modern IPTV streaming platform built on iptv-org data.
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.services.cache import get_cache
from app.services.data_sync import get_sync_service
from app.routers import channels, streams, epg

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting IPTV Web Backend...")
    
    # Initialize cache database
    cache = await get_cache()
    logger.info("Cache initialized")
    
    # Sync data on startup (if cache is empty)
    channels_data, _ = await cache.get_channels(page=1, per_page=1)
    if not channels_data:
        logger.info("Cache empty, syncing data from iptv-org...")
        sync_service = get_sync_service()
        results = await sync_service.sync_all()
        logger.info(f"Data sync complete: {results}")
    else:
        logger.info("Cache populated, skipping initial sync")
    
    yield
    
    logger.info("Shutting down IPTV Web Backend...")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A secure IPTV streaming web application",
    lifespan=lifespan
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(channels.router)
app.include_router(streams.router)
app.include_router(epg.router)


# API endpoints
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


@app.get("/api/stats")
async def get_stats():
    """Get database statistics."""
    cache = await get_cache()
    channels, total_channels = await cache.get_channels(page=1, per_page=1)
    countries = await cache.get_countries()
    categories = await cache.get_categories()
    
    return {
        "total_channels": total_channels,
        "total_countries": len(countries),
        "total_categories": len(categories),
        "countries_with_channels": len([c for c in countries if c.get("channel_count", 0) > 0])
    }


# Serve frontend static files
frontend_path = Path(__file__).parent.parent.parent / "frontend"

if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")
    app.mount("/css", StaticFiles(directory=frontend_path / "css"), name="css")
    app.mount("/js", StaticFiles(directory=frontend_path / "js"), name="js")
    
    @app.get("/")
    async def serve_index():
        """Serve the frontend index.html."""
        return FileResponse(frontend_path / "index.html")
    
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve SPA for any non-API route."""
        file_path = frontend_path / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_path / "index.html")


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
