"""Agent, analytics, notification, audit, cluster schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import RoleEnum


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str
    role: RoleEnum
    is_active: bool
    title: str | None = None
    skills: list[str] = []
    availability: str = "online"
    open_ticket_count: int = 0
    last_active_at: datetime | None = None


class AgentCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: RoleEnum = RoleEnum.AGENT
    title: str | None = None
    skills: list[str] = Field(default_factory=list)
    max_concurrent_tickets: int | None = Field(default=None, ge=1)


class AgentUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    role: RoleEnum | None = None
    title: str | None = None
    skills: list[str] | None = None
    availability: str | None = None
    max_concurrent_tickets: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class DateRange(BaseModel):
    start: datetime | None = None
    end: datetime | None = None


class AnalyticsOverview(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    avg_resolution_minutes: float | None = None
    avg_first_response_minutes: float | None = None
    sla_compliance_rate: float | None = None
    tickets_by_status: dict[str, int] = {}
    tickets_by_priority: dict[str, int] = {}
    tickets_by_category: dict[str, int] = {}
    top_agents: list[dict] = []


class AgentPerformance(BaseModel):
    agent_id: str
    agent_name: str
    tickets_resolved: int
    tickets_created: int
    total_responses: int
    avg_resolution_minutes: float | None = None
    avg_first_response_minutes: float | None = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    title: str
    message: str | None = None
    link: str | None = None
    read_at: datetime | None = None
    created_at: datetime


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_id: str | None = None
    actor_email: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    metadata_json: str | None = None
    ip_address: str | None = None
    created_at: datetime


class PagedAudit(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int


class HealthOut(BaseModel):
    status: str
    database: str
    redis: str
    ai_configured: bool
    version: str
