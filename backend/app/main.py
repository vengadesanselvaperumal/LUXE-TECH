from contextlib import asynccontextmanager
import logging
from urllib.parse import urlparse
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from app.config import get_settings
from app.database import engine, init_db
from app.routers import (
    auth,
    collections,
    dashboard,
    forecasts,
    images,
    news,
    products,
    prophecy,
    retail,
    search,
    signals,
    submissions,
    trends,
    videos,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("luxe_tech")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Local SQLite may bootstrap itself; cloud PostgreSQL must be migrated explicitly.
    logger.info("Initializing LUXE.TECH Fashion Intelligence platform...")
    init_db()
    logger.info("Database schema verified; automatic demo seeding is disabled.")

    yield

    # Shutdown
    logger.info("Shutting down LUXE.TECH platform.")


app = FastAPI(
    title="LUXE.TECH — Fashion Intelligence Platform",
    description="Fashion intelligence using the configured SQL database, optional Gemini, and local computer vision and forecasting.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)

# Standardized Error Handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail
            },
            "meta": {"path": str(request.url.path)}
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    error_msg = "; ".join([f"{err['loc'][-1]}: {err['msg']}" for err in exc.errors()])
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": error_msg
            },
            "meta": {"path": str(request.url.path), "details": exc.errors()}
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Intelligence temporarily unavailable. We couldn't process this request."
            },
            "meta": {"path": str(request.url.path)}
        }
    )


# Health check
@app.get("/api/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Database health check failed (%s).", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Database is unavailable.")

    database_host = urlparse(settings.DATABASE_URL).hostname or ""
    supabase_postgres_configured = (
        engine.dialect.name == "postgresql" and "supabase" in database_host.lower()
    )
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "service": "LUXE.TECH Fashion Intelligence",
            "database_backend": engine.dialect.name,
            "database_connected": True,
            "supabase_postgres_configured": supabase_postgres_configured,
            "supabase_postgres_connected": supabase_postgres_configured,
            "supabase_storage_credentials_configured": settings.has_supabase,
            "supabase_storage_status": "configured_unverified" if settings.has_supabase else "not_configured",
            "gemini_configured": settings.has_gemini,
            "gemini_model": settings.GEMINI_MODEL,
            "engine": "FastAPI + Local ML/CV + Optional Gemini",
        },
        "error": None,
        "meta": {}
    }


# Register Routers
app.include_router(auth.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(trends.router, prefix="/api")
app.include_router(signals.router, prefix="/api")
app.include_router(collections.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(retail.router, prefix="/api")
app.include_router(forecasts.router, prefix="/api")
app.include_router(prophecy.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(submissions.router, prefix="/api")
app.include_router(videos.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
