"""Knowledge Base schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import KBArticleStatus


class KBArticleCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    content: str = Field(min_length=10)
    summary: str | None = None
    category_id: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)


class KBArticleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    content: str | None = Field(default=None, min_length=10)
    summary: str | None = None
    category_id: str | None = None
    tags: list[str] | None = None
    change_summary: str | None = Field(default=None, max_length=255)


class KBArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    content: str
    summary: str | None = None
    status: KBArticleStatus
    tags: list[str] = []
    view_count: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    usage_count: int = 0
    category_id: str | None = None
    category: str | None = None
    author_name: str | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    current_version: int = 1


class KBArticleVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: int
    title: str
    content: str
    summary: str | None = None
    change_summary: str | None = None
    changed_by: str | None = None
    created_at: datetime


class PagedKB(BaseModel):
    items: list[KBArticleOut]
    total: int
    page: int
    page_size: int
    pages: int


class KBFeedbackCreate(BaseModel):
    helpful: bool


class ArticleStats(BaseModel):
    views: int
    helpful: int
    not_helpful: int
    usage: int
    helpful_rate: float


class VersionRollbackRequest(BaseModel):
    version: int = Field(ge=1)
