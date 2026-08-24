"""User, role, and agent models."""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import RoleEnum


class Role(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    permissions: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )  # JSON array of permission strings


class User(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
    external_auth_id: Mapped[str] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(
        String(32), default=RoleEnum.AGENT, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def is_admin(self) -> bool:
        return self.role == RoleEnum.ADMIN

    def touch_last_active(self) -> None:
        self.last_active_at = datetime.now(timezone.utc)


class Agent(User):
    """Specialization of User representing a support agent.

    Kept as a subclass table so agents share auth identity while carrying
    support-specific fields (availability, workload hints, skills).
    """

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    phone: Mapped[str] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(128), nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    availability: Mapped[str] = mapped_column(
        String(16), default="online", nullable=False
    )  # online / offline / away
    max_concurrent_tickets: Mapped[int] = mapped_column(nullable=True)
