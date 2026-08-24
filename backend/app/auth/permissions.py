"""Server-side RBAC permission definitions.

Every protected endpoint checks a permission here server-side. The client's
reported role is never trusted; the role on the authenticated JWT/session is
mapped to a permission set by the backend.

Permission strings use the form ``{resource}.{action}``.
"""
from __future__ import annotations

from app.models.enums import RoleEnum

# Global permission catalog.
TICKETS_READ = "tickets.read"
TICKETS_CREATE = "tickets.create"
TICKETS_UPDATE = "tickets.update"
TICKETS_ASSIGN = "tickets.assign"
TICKETS_DELETE = "tickets.delete"
TICKETS_REPLY = "tickets.reply"
TICKETS_INTERNAL_NOTE = "tickets.internal_note"
TICKETS_CLOSE = "tickets.close"
TICKETS_MERGE = "tickets.merge"

KB_READ = "kb.read"
KB_CREATE = "kb.create"
KB_UPDATE = "kb.update"
KB_PUBLISH = "kb.publish"
KB_DELETE = "kb.delete"

AGENTS_READ = "agents.read"
AGENTS_CREATE = "agents.create"
AGENTS_UPDATE = "agents.update"
AGENTS_DEACTIVATE = "agents.deactivate"

ANALYTICS_READ = "analytics.read"
AUDIT_READ = "audit.read"
ADMIN_MANAGE = "admin.manage"
AI_USE = "ai.use"

# Permission set per role. Senior agents add KB publish + merge over agents;
# admins get everything.
ROLE_PERMISSIONS: dict[RoleEnum, set[str]] = {
    RoleEnum.ADMIN: {
        TICKETS_READ, TICKETS_CREATE, TICKETS_UPDATE, TICKETS_ASSIGN,
        TICKETS_DELETE, TICKETS_REPLY, TICKETS_INTERNAL_NOTE, TICKETS_CLOSE,
        TICKETS_MERGE,
        KB_READ, KB_CREATE, KB_UPDATE, KB_PUBLISH, KB_DELETE,
        AGENTS_READ, AGENTS_CREATE, AGENTS_UPDATE, AGENTS_DEACTIVATE,
        ANALYTICS_READ, AUDIT_READ, ADMIN_MANAGE, AI_USE,
    },
    RoleEnum.SENIOR_AGENT: {
        TICKETS_READ, TICKETS_CREATE, TICKETS_UPDATE, TICKETS_ASSIGN,
        TICKETS_REPLY, TICKETS_INTERNAL_NOTE, TICKETS_CLOSE, TICKETS_MERGE,
        KB_READ, KB_CREATE, KB_UPDATE, KB_PUBLISH,
        AGENTS_READ,
        ANALYTICS_READ, AI_USE,
    },
    RoleEnum.AGENT: {
        TICKETS_READ, TICKETS_CREATE, TICKETS_UPDATE, TICKETS_ASSIGN,
        TICKETS_REPLY, TICKETS_INTERNAL_NOTE, TICKETS_CLOSE,
        KB_READ, KB_CREATE, KB_UPDATE,
        AGENTS_READ,
        ANALYTICS_READ, AI_USE,
    },
}


def permissions_for_role(role: RoleEnum) -> set[str]:
    return ROLE_PERMISSIONS.get(role, set())


def role_has_permission(role: RoleEnum, permission: str) -> bool:
    return permission in permissions_for_role(role)
