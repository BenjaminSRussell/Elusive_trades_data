"""
Main FastAPI application for the Fugitive Data Pipeline API.
Provides RESTful endpoints for part lookup and replacement queries.
"""

import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from phase5_api.routers import lookup
from phase5_api.models.schemas import HealthResponse, ErrorResponse
from phase5_api.services.lookup_service import LookupService
from config.error_handling import setup_logging, error_tracker

# Setup logging
setup_logging(log_level='INFO', log_file='logs/api.log')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Fugitive Data Pipeline API...")
    logger.info("Initializing services...")

    yield

    # Shutdown
    logger.info("Shutting down API...")


# Create FastAPI app
app = FastAPI(
    title="Fugitive Data Pipeline API",
    description="""
    **HVAC/Plumbing Parts Replacement Lookup API**

    This API provides intelligent part replacement lookups using:
    - Custom NLP-extracted knowledge from manufacturer catalogs
    - "Tribal knowledge" from HVAC forums
    - Multi-degree replacement chain traversal via Neo4j graph database

    ## Features

    - **Part Lookup**: Get detailed information about any HVAC/plumbing part
    - **Specification Search**: Find parts by technical specs (capacitance, voltage, HP, etc.)
    - **Replacement Chains**: Discover 1st, 2nd, 3rd degree replacements automatically
    - **Tribal Knowledge**: Access forum-sourced compatibility information

    ## Technology Stack

    - **FastAPI** (async/await for high concurrency)
    - **Neo4j** (graph database for replacement chains)
    - **PostgreSQL** (evidence store)
    - **spaCy** (custom NER/RE for knowledge extraction)
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add response time header to all requests."""
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )

    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    error_tracker.record_error(
        component='api',
        error_type='unhandled_exception',
        message=str(exc),
        details={'path': str(request.url.path)}
    )

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred",
            details={"type": type(exc).__name__}
        ).dict()
    )


# Include routers
app.include_router(lookup.router)


# Root endpoint
@app.get(
    "/",
    summary="API Root",
    description="Welcome message and API information"
)
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Fugitive Data Pipeline API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# Health check endpoint
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check API and backend service health"
)
async def health_check():
    """
    Health check endpoint.

    Returns status of:
    - API server
    - Neo4j graph database
    - PostgreSQL evidence store
    """
    lookup_service = LookupService()
    services = await lookup_service.health_check()

    # Determine overall status
    all_healthy = all(status == 'connected' for status in services.values())
    status = "healthy" if all_healthy else "degraded"

    return HealthResponse(
        status=status,
        version="1.0.0",
        services=services
    )


# Error stats endpoint (for debugging)
@app.get(
    "/debug/errors",
    include_in_schema=False
)
async def get_error_stats():
    """Get error statistics (debug only)."""
    return error_tracker.get_error_summary()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
