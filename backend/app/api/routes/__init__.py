"""API router aggregation."""
from fastapi import APIRouter

from app.api.routes import (
    agents,
    analytics,
    audit,
    auth,
    health,
    kb,
    misc,
    notifications,
    tickets,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(tickets.router)
api_router.include_router(kb.router)
api_router.include_router(agents.router)
api_router.include_router(analytics.router)
api_router.include_router(notifications.router)
api_router.include_router(audit.router)
api_router.include_router(health.router)
api_router.include_router(misc.router)
