"""Main FastAPI application for Alexandria Web UI."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from web import __version__
from web.api import auth, authors, items, piles, review, series, settings as admin_settings, stats, tts
from web.config import settings
from web.database import SessionLocal
from web.middleware.rate_limit import limiter
from web.startup import run_startup_tasks

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown tasks."""
    # Startup
    logger.info("Starting Alexandria Web UI...")

    # Run all startup tasks (migrations, seeding, admin creation)
    db = SessionLocal()
    try:
        run_startup_tasks(db)
    finally:
        db.close()

    yield

    # Shutdown
    logger.info("Shutting down Alexandria Web UI...")


app = FastAPI(
    title="Alexandria",
    description="Bibliotheca Alexandria - A self-hosted digital library",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return {"detail": "Rate limit exceeded. Please try again later."}

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(auth.router)
app.include_router(items.router, prefix="/api")
app.include_router(authors.router, prefix="/api")
app.include_router(series.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(piles.router, prefix="/api")
app.include_router(review.router, prefix="/api")
app.include_router(admin_settings.router)  # Admin settings (includes prefix)
app.include_router(tts.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": __version__}


# Serve static frontend files if they exist
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "build"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "web.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
