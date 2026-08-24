"""Notification model (in-app). Providers for email/push are a stub abstraction."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Notification(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user", "user_id"),)

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    link: Mapped[str] = mapped_column(String(255), nullable=True)

    @property
    def is_read(self) -> bool:
        return self.read_at is not None
