"""Main FastAPI application for the Lexi case search API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.routes import cases, meta


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""
    # Startup
    setup_logging()
    logger = get_logger(__name__)
    logger.info("Starting Lexi Case Search API")

    yield

    # Shutdown
    logger.info("Shutting down Lexi Case Search API")


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    description="A FastAPI backend that proxies and normalizes case-search results from Jagriti (https://e-jagriti.gov.in)",
    version=settings.version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "detail": "The requested resource was not found",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle internal server errors."""
    logger = get_logger(__name__)
    logger.error(f"Internal server error on {request.url.path}: {exc}")

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred",
            "message": "Please try again later or contact support if the problem persists",
        },
    )


# Include routers
app.include_router(meta.router)
app.include_router(cases.router)


# Health check endpoint
@app.get(
    "/health",
    tags=["health"],
    summary="Health check",
    description="Check if the API is running and healthy",
)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.version,
        "service": settings.app_name,
    }


# Root endpoint
@app.get(
    "/",
    tags=["root"],
    summary="API information",
    description="Get basic information about the API",
)
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "docs_url": "/docs",
        "health_url": "/health",
        "endpoints": {
            "states": "/states",
            "commissions": "/commissions/{state_id}",
            "case_search": {
                "by_case_number": "/cases/by-case-number",
                "by_complainant": "/cases/by-complainant",
                "by_respondent": "/cases/by-respondent",
                "by_complainant_advocate": "/cases/by-complainant-advocate",
                "by_respondent_advocate": "/cases/by-respondent-advocate",
                "by_industry_type": "/cases/by-industry-type",
                "by_judge": "/cases/by-judge",
            },
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
