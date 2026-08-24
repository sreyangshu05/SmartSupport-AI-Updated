"""Import all models so Alembic autogenerate and metadata see every table."""
from app.models.base import Base
from app.models.user import Agent, Role, User
from app.models.ticket import (
    Customer,
    SLAPolicy,
    Ticket,
    TicketAttachment,
    TicketCategory,
    TicketEvent,
    TicketResponse,
    TicketSLA,
    TicketTag,
)
from app.models.kb import (
    KBArticle,
    KBArticleVersion,
    KBArticleView,
    KBFeedback,
    TicketKBSuggestion,
)
from app.models.ai import (
    AIGeneration,
    KBArticleEmbedding,
    TicketClassification,
    TicketEmbedding,
)
from app.models.notification import Notification
from app.models.audit import AuditLog

__all__ = [
    "Base",
    "Agent",
    "Role",
    "User",
    "Customer",
    "SLAPolicy",
    "Ticket",
    "TicketAttachment",
    "TicketCategory",
    "TicketEvent",
    "TicketResponse",
    "TicketSLA",
    "TicketTag",
    "KBArticle",
    "KBArticleVersion",
    "KBArticleView",
    "KBFeedback",
    "TicketKBSuggestion",
    "AIGeneration",
    "KBArticleEmbedding",
    "TicketClassification",
    "TicketEmbedding",
    "Notification",
    "AuditLog",
]
