"""Knowledge Base domain models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin, new_uuid
from app.models.enums import KBArticleStatus


class KBArticle(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "kb_articles"
    __table_args__ = (
        Index("ix_kb_articles_category_id", "category_id"),
        Index("ix_kb_articles_status", "status"),
        Index("ix_kb_articles_created_at", "created_at"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    category_id: Mapped[str] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[KBArticleStatus] = mapped_column(
        String(16), default=KBArticleStatus.DRAFT, nullable=False
    )
    author_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    not_helpful_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class KBArticleVersion(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "kb_article_versions"

    article_id: Mapped[str] = mapped_column(
        ForeignKey("kb_articles.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    changed_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    change_summary: Mapped[str] = mapped_column(String(255), nullable=True)


class KBFeedback(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "kb_feedback"

    article_id: Mapped[str] = mapped_column(
        ForeignKey("kb_articles.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)


class KBArticleView(TimestampMixin, UUIDMixin, Base):
    __tablename__ = "kb_article_views"

    article_id: Mapped[str] = mapped_column(
        ForeignKey("kb_articles.id", ondelete="CASCADE"), nullable=False
    )
    viewer_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class TicketKBSuggestion(Base):
    __tablename__ = "ticket_kb_suggestions"
    __table_args__ = (Index("ix_ticket_kb_suggestions_ticket", "ticket_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    ticket_id: Mapped[str] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    article_id: Mapped[str] = mapped_column(
        ForeignKey("kb_articles.id", ondelete="CASCADE"), nullable=False
    )
    relevance_score: Mapped[float] = mapped_column(nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=True)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=True)
    rejected: Mapped[bool] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
