"""Audit log routes (admin only)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser, require_permission
from app.auth.permissions import AUDIT_READ
from app.core.database import get_db
from app.schemas.admin import PagedAudit
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=PagedAudit)
def list_audit(
    current: Annotated[CurrentUser, Depends(require_permission(AUDIT_READ))],
    db: Annotated[Session, Depends(get_db)],
    actor_id: str | None = None,
    resource_type: str | None = None,
    action: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    return AuditService(db).list_logs(
        actor_id=actor_id, resource_type=resource_type, action=action,
        page=page, page_size=page_size,
    )
