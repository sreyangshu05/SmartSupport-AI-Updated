"""Ticket schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import (
    EventType,
    ResponseType,
    SLABreachStatus,
    TicketPriority,
    TicketStatus,
)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    color: str


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str | None = None
    tier: str
    open_tickets: int = 0
    resolved_tickets: int = 0
    total_tickets: int = 0


class AgentRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    role: str


class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10, max_length=20000)
    priority: TicketPriority = TicketPriority.MEDIUM
    category_id: str | None = None
    customer_email: EmailStr
    customer_name: str | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)


class TicketUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10, max_length=20000)
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category_id: str | None = None
    assigned_to: str | None = None

    @field_validator("category_id", "assigned_to", mode="before")
    @classmethod
    def _empty_to_none(cls, v):
        if v == "":
            return None
        return v


class TicketResponseCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20000)
    is_internal: bool = False


class TicketResponseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    content: str
    response_type: ResponseType
    is_internal: bool
    created_at: datetime
    author_name: str | None = None
    author_role: str | None = None


class TicketEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: EventType
    old_value: str | None = None
    new_value: str | None = None
    metadata_json: str | None = None
    created_at: datetime
    actor_name: str | None = None


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_number: str
    subject: str
    description: str
    summary: str | None = None
    status: TicketStatus
    priority: TicketPriority
    category: CategoryOut | None = None
    assigned_agent: AgentRef | None = None
    created_by_email: str
    customer: CustomerOut | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    sla_status: SLABreachStatus = SLABreachStatus.GREEN
    sla_due_at: datetime | None = None


class TicketDetail(TicketOut):
    responses: list[TicketResponseOut] = []
    events: list[TicketEventOut] = []
    tags: list[str] = []


class PagedTickets(BaseModel):
    items: list[TicketOut]
    total: int
    page: int
    page_size: int
    pages: int


class KBArticleRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    summary: str | None = None


class KBSuggestionOut(BaseModel):
    article: KBArticleRef
    relevance_score: float
    reason: str | None = None


class SimilarTicketOut(BaseModel):
    ticket: TicketOut
    similarity_score: float


class ClassificationOut(BaseModel):
    category: CategoryOut | None = None
    category_id: str | None = None
    confidence: float
    low_confidence: bool
    reasoning: str | None = None
    model: str | None = None


class SummaryOut(BaseModel):
    summary: str
    model: str | None = None
    sources: list[str] = []


class DraftReplyOut(BaseModel):
    draft: str
    model: str | None = None
    sources: list[KBArticleRef] = []


class ClusterOut(BaseModel):
    id: str
    name: str
    ticket_count: int
    confidence: float
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    is_trending: bool
    representative_ticket_ids: list[str] = []
