"""
PrepAI — FastAPI application entry point.
Creates the FastAPI app with lifespan, mounts Socket.IO, includes all routers.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from apps.api.core.config import get_settings
from apps.api.db.postgres import init_db, close_db
from apps.api.db.mongo import connect_mongo, close_mongo
from apps.api.core.auth import close_redis

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown events."""
    # ── Startup ──────────────────────────────────────────────────────────
    logger.info("🚀 Starting PrepAI API...")

    try:
        await init_db()
        logger.info("✅ PostgreSQL connected")
    except Exception as e:
        logger.error(f"❌ PostgreSQL connection failed: {e}")

    try:
        await connect_mongo()
        logger.info("✅ MongoDB connected")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")

    logger.info(f"✅ PrepAI API ready (env={settings.ENVIRONMENT})")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("🛑 Shutting down PrepAI API...")
    await close_db()
    await close_mongo()
    await close_redis()
    logger.info("✅ All connections closed")


# Create FastAPI app
app = FastAPI(
    title="PrepAI API",
    description="AI-powered mock interview coaching platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS Middleware ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request ID Middleware ────────────────────────────────────────────────────
@app.middleware("http")
async def add_request_id(request: Request, call_next) -> Response:
    """Add a unique request ID to every request for tracing."""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ── Include Routers ──────────────────────────────────────────────────────────
from apps.api.user.router import router as user_router
from apps.api.interview.router import router as interview_router
from apps.api.feedback.router import router as feedback_router

app.include_router(user_router, prefix="/api/v1")
app.include_router(interview_router, prefix="/api/v1")
app.include_router(feedback_router, prefix="/api/v1")


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "prepai-api",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


# ── Mount Socket.IO ─────────────────────────────────────────────────────────
from apps.api.core.websocket import socket_app as sio_asgi_app

# Create the combined ASGI app: FastAPI + Socket.IO
# Socket.IO is mounted at /ws
app.mount("/ws", sio_asgi_app)

# The main ASGI app to run with uvicorn
# Usage: uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
