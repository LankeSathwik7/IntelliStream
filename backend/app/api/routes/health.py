"""Health check endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "intellistream-api",
        "version": "1.0.0",
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness check for container orchestration."""
    checks = {
        "database": "ok",
        "cache": "ok",
        "llm": "ok",
    }

    # Check if services are configured
    if not settings.supabase_url:
        checks["database"] = "not_configured"
    if not settings.upstash_redis_rest_url:
        checks["cache"] = "not_configured"
    if not settings.groq_api_key:
        checks["llm"] = "not_configured"

    all_ok = all(v == "ok" for v in checks.values())

    return {
        "status": "ready" if all_ok else "degraded",
        "checks": checks,
    }


@router.get("/health/live")
async def liveness_check():
    """Liveness check - always returns ok if the server is running."""
    return {"status": "alive"}
