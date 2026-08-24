"""Analytics routes — metrics derived from persisted data."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser, require_permission
from app.auth.permissions import ANALYTICS_READ
from app.core.database import get_db
from app.schemas.admin import AnalyticsOverview
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def overview(
    current: Annotated[CurrentUser, Depends(require_permission(ANALYTICS_READ))],
    db: Annotated[Session, Depends(get_db)],
    start: datetime | None = None,
    end: datetime | None = None,
):
    return AnalyticsService(db).overview(start, end)


@router.get("/agents")
def agent_performance(
    current: Annotated[CurrentUser, Depends(require_permission(ANALYTICS_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    return AnalyticsService(db).agent_performance()
