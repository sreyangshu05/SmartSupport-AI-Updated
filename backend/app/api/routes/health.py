"""Health and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from redis import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine
from app.schemas.admin import HealthOut

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthOut)
def health():
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    redis_status = "ok"
    if settings.REDIS_ENABLED:
        try:
            r = Redis.from_url(settings.REDIS_URL, socket_timeout=1)
            r.ping()
        except Exception:
            redis_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "redis": redis_status,
        "ai_configured": bool(settings.AI_API_KEY),
        "version": "1.0.0",
    }


@router.get("/ready")
def readiness():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        from fastapi import HTTPException
        from fastapi import status as st
        raise HTTPException(status_code=st.HTTP_503_SERVICE_UNAVAILABLE, detail="database unavailable")
    return {"ready": True}
