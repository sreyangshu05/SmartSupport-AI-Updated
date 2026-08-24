"""In-app notification service. Provider abstraction surface for email/push."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def notify(
        self,
        user_id: str,
        *,
        type: str,
        title: str,
        message: str | None = None,
        link: str | None = None,
    ) -> Notification:
        n = self.record(
            user_id=user_id, type=type, title=title,
            message=message, link=link,
        )
        self.db.commit()
        self.db.refresh(n)
        return n

    def record(
        self,
        user_id: str,
        *,
        type: str,
        title: str,
        message: str | None = None,
        link: str | None = None,
    ) -> Notification:
        """Add a notification without committing.

        Lets callers that are already inside a transactional write (ticket
        creation, reply, assignment) include the notification in the same
        commit, preserving atomicity.
        """
        n = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link=link,
        )
        self.db.add(n)
        self.db.flush()
        return n

    def list_for_user(self, user_id: str, *, unread_only: bool = False) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))
        stmt = stmt.order_by(Notification.created_at.desc()).limit(100)
        return list(self.db.scalars(stmt))

    def mark_read(self, notification_id: str, user_id: str, *, read: bool = True) -> Notification | None:
        n = self.db.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        if n is None:
            return None
        n.read_at = datetime.now(timezone.utc) if read else None
        n.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(n)
        return n
