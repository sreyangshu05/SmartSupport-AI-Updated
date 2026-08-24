"""Enumerated value types shared across the domain."""
from __future__ import annotations

import enum


def sval(value) -> str:
    """Return a plain string for an enum-or-str value.

    SQLAlchemy returns String-backed enum columns as plain str at read time,
    while enums constructed in Python carry ``.value``. This helper normalizes
    both so callers never need to know which form they hold.
    """
    if isinstance(value, enum.Enum):
        return str(value.value)
    return str(value)


class RoleEnum(str, enum.Enum):
    ADMIN = "admin"
    SENIOR_AGENT = "senior_agent"
    AGENT = "agent"


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    WAITING_FOR_INTERNAL = "waiting_for_internal"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ResponseType(str, enum.Enum):
    CUSTOMER = "customer"
    AGENT = "agent"
    INTERNAL_NOTE = "internal_note"
    SYSTEM = "system"


class KBArticleStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class EventType(str, enum.Enum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    CATEGORY_CHANGED = "category_changed"
    ASSIGNED = "assigned"
    REASSIGNED = "reassigned"
    RESPONSE_ADDED = "response_added"
    INTERNAL_NOTE_ADDED = "internal_note_added"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"
    DUPLICATE_MARKED = "duplicate_marked"
    MERGED = "merged"


class SLABreachStatus(str, enum.Enum):
    GREEN = "green"
    WARNING = "warning"
    BREACHED = "breached"


class SLAType(str, enum.Enum):
    FIRST_RESPONSE = "first_response"
    RESOLUTION = "resolution"
