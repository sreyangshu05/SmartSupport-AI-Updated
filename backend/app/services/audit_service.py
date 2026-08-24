"""Append-only audit logging."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def _record(
        self,
        *,
        actor_id: str | None,
        actor_email: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        metadata: dict | None = None,
        request: Request | None = None,
    ) -> AuditLog:
        ip = request.client.host if request and request.client else None
        ua = request.headers.get("user-agent") if request else None
        entry = AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata_json=json.dumps(metadata) if metadata else None,
            ip_address=ip,
            user_agent=ua[:255] if ua else None,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def commit(self) -> None:
        """Persist audited actions in the same transaction as the primary write."""
        self.db.commit()

    def log(
        self,
        *,
        actor_id: str | None,
        actor_email: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        metadata: dict | None = None,
        request: Request | None = None,
    ) -> AuditLog:
        """Audit with its own commit (for independent lifecycle actions)."""
        entry = self._record(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            request=request,
        )
        self.db.commit()
        return entry

    def record(
        self,
        *,
        actor_id: str | None,
        actor_email: str | None,
        action: str,
        resource_type: str,
        resource_id: str | None = None,
        metadata: dict | None = None,
        request: Request | None = None,
    ) -> AuditLog:
        """Audit within the caller's transaction (caller commits)."""
        return self._record(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata,
            request=request,
        )

    def list_logs(
        self,
        *,
        actor_id: str | None = None,
        resource_type: str | None = None,
        action: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        stmt = select(AuditLog)
        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
        if resource_type:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.order_by(AuditLog.created_at.desc()) \
            .offset((page - 1) * page_size).limit(page_size)
        items = self.db.scalars(stmt).all()
        pages = max(1, (total + page_size - 1) // page_size)
        return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}
