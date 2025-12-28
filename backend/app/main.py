"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, documents, health
from app.api.routes import settings as settings_router
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    logger.info(f"Starting IntelliStream API in {settings.environment} mode")
    logger.info(f"Services configured: {settings.is_configured}")
    yield
    # Shutdown
    logger.info("Shutting down IntelliStream API")


app = FastAPI(
    title="IntelliStream API",
    description="Real-Time Agentic RAG Intelligence Platform with 6-agent LangGraph workflow",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS Configuration - Restrict in production
cors_origins = (
    ["*"] if not settings.is_production
    else [settings.frontend_url, "https://intellistream.pages.dev"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True if settings.is_production else False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(settings_router.router, prefix="/api/settings", tags=["Settings"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "IntelliStream API",
        "version": "1.0.0",
        "description": "Real-Time Agentic RAG Intelligence Platform",
        "status": "running",
        "environment": settings.environment,
        "docs": "/docs" if settings.debug else "disabled",
        "endpoints": {
            "health": "/health",
            "chat": "/api/chat",
            "chat_stream": "/api/chat/stream",
            "export_pdf": "/api/chat/export/pdf",
            "documents": "/api/documents",
            "settings": "/api/settings",
        },
    }
