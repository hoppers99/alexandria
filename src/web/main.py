"""Main FastAPI application for Alexandria Web UI."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from web import __version__
from web.api import authors, items, piles, review, series, stats
from web.config import settings

app = FastAPI(
    title="Alexandria",
    description="Bibliotheca Alexandria - A self-hosted digital library",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(items.router, prefix="/api")
app.include_router(authors.router, prefix="/api")
app.include_router(series.router, prefix="/api")
app.include_router(stats.router, prefix="/api")
app.include_router(piles.router, prefix="/api")
app.include_router(review.router, prefix="/api")


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
