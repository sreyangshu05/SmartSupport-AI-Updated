"""Ticket domain models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, new_uuid
from app.models.enums import (
    EventType,
    ResponseType,
    SLABreachStatus,
    SLAType,
    TicketPriority,
    TicketStatus,
)


class TicketCategory(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    color: Mapped[str] = mapped_column(String(32), default="#3B82F6", nullable=False)


class Customer(TimestampMixin, UUIDMixin, Base):
    """A customer identity aggregated across their tickets."""

    __tablename__ = "customers"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(64), nullable=True)
    tier: Mapped[str] = mapped_column(String(32), default="standard", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Ticket(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_priority", "priority"),
        Index("ix_tickets_assigned_to", "assigned_to"),
        Index("ix_tickets_category_id", "category_id"),
        Index("ix_tickets_created_at", "created_at"),
        Index("ix_tickets_customer_id", "customer_id"),
    )

    ticket_number: Mapped[str] = mapped_column(
        String(16), unique=True, nullable=False
    )
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[TicketStatus] = mapped_column(
        String(32), default=TicketStatus.OPEN, nullable=False
    )
    priority: Mapped[TicketPriority] = mapped_column(
        String(16), default=TicketPriority.MEDIUM, nullable=False
    )

    category_id: Mapped[str] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_email: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )

    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_response_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sla_status: Mapped[SLABreachStatus] = mapped_column(
        String(16), default=SLABreachStatus.GREEN, nullable=False
    )
    is_duplicate_of: Mapped[str] = mapped_column(
        ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True
    )

    category: Mapped["TicketCategory"] = relationship()
    assignments: Mapped[list["TicketResponse"]] = relationship("TicketResponse", back_populates="ticket")
    events: Mapped[list["TicketEvent"]] = relationship(
        "TicketEvent", back_populates="ticket", cascade="all, delete-orphan", uselist=True
    )


class TicketResponse(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "ticket_responses"
    __table_args__ = (Index("ix_ticket_responses_ticket_id", "ticket_id"),)

    ticket_id: Mapped[str] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    response_type: Mapped[ResponseType] = mapped_column(
        String(24), default=ResponseType.AGENT, nullable=False
    )
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ticket: Mapped["Ticket"] = relationship(back_populates="assignments")


class TicketAttachment(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "ticket_attachments"

    ticket_id: Mapped[str] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    response_id: Mapped[str] = mapped_column(
        ForeignKey("ticket_responses.id", ondelete="SET NULL"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)


class TicketTag(Base):
    __tablename__ = "ticket_tags"
    __table_args__ = (
        Index("ix_ticket_tags_tag", "tag"),
        Index("ix_ticket_tags_ticket_id", "ticket_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_uuid
    )
    ticket_id: Mapped[str] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[str] = mapped_column(String(64), nullable=False)


class TicketEvent(Base):
    """Append-only timeline of ticket state changes."""

    __tablename__ = "ticket_events"
    __table_args__ = (Index("ix_ticket_events_ticket_id", "ticket_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    ticket_id: Mapped[str] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    actor_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[EventType] = mapped_column(String(32), nullable=False)
    old_value: Mapped[str] = mapped_column(String(255), nullable=True)
    new_value: Mapped[str] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    ticket: Mapped["Ticket"] = relationship(back_populates="events")


class SLAPolicy(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "sla_policies"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sla_type: Mapped[SLAType] = mapped_column(
        String(24), default=SLAType.FIRST_RESPONSE, nullable=False
    )
    priority: Mapped[TicketPriority] = mapped_column(
        String(16), nullable=False
    )
    target_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_minutes: Mapped[int] = mapped_column(Integer, nullable=False)


class TicketSLA(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "ticket_sla"

    ticket_id: Mapped[str] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    sla_type: Mapped[SLAType] = mapped_column(
        String(24), nullable=False
    )
    policy_id: Mapped[str] = mapped_column(
        ForeignKey("sla_policies.id", ondelete="SET NULL"), nullable=True
    )
    target_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[SLABreachStatus] = mapped_column(
        String(16), default=SLABreachStatus.GREEN, nullable=False
    )
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
