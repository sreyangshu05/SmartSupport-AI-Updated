"""Agent management routes."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser, require_permission
from app.auth.permissions import AGENTS_CREATE, AGENTS_DEACTIVATE, AGENTS_READ, AGENTS_UPDATE
from app.core.database import get_db
from app.models.enums import TicketStatus, sval
from app.models.ticket import Ticket
from app.models.user import Agent, User
from app.schemas.admin import AgentCreate, AgentOut, AgentUpdate
from app.auth.security import hash_password
from app.services.audit_service import AuditService

router = APIRouter(prefix="/agents", tags=["agents"])

ACTIVE = (TicketStatus.OPEN, TicketStatus.IN_PROGRESS,
          TicketStatus.WAITING_FOR_CUSTOMER, TicketStatus.WAITING_FOR_INTERNAL)


def _serialize_agent(u: User, agent: Agent | None = None, open_count: int | None = None) -> dict:
    # Agent subclass rows may or may not exist for a given user; fall back to
    # defaults so legacy/plain users still serialize cleanly.
    return {
        "id": str(u.id), "email": u.email, "full_name": u.full_name,
        "role": sval(u.role), "is_active": u.is_active,
        "title": (agent.title if agent is not None else None),
        "skills": (agent.skills if agent is not None else []),
        "availability": (agent.availability if agent is not None else "online"),
        "open_ticket_count": open_count or 0,
        "last_active_at": u.last_active_at,
    }


@router.get("", response_model=list[AgentOut])
def list_agents(
    current: Annotated[CurrentUser, Depends(require_permission(AGENTS_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    users = db.scalars(select(User).order_by(User.created_at)).all()
    agents = {a.id: a for a in db.scalars(select(Agent)).all()}
    out = []
    for u in users:
        open_count = db.scalar(
            select(func.count()).where(Ticket.assigned_to == str(u.id), Ticket.status.in_(ACTIVE))
        ) or 0
        out.append(_serialize_agent(u, agents.get(str(u.id)), open_count))
    return out


@router.post("", response_model=AgentOut, status_code=201)
def create_agent(
    body: AgentCreate,
    current: Annotated[CurrentUser, Depends(require_permission(AGENTS_CREATE))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(409, "An agent with that email already exists")
    from app.models.enums import RoleEnum
    # Agent is joined-table inheritance over User: one object carries both the
    # parent (auth/identity) and child (support-specific) fields. Creating a
    # single Agent inserts into both `users` and `agents`.
    agent = Agent(
        email=body.email,
        full_name=body.full_name,
        role=body.role or RoleEnum.AGENT,
        password_hash=hash_password("changeme123"),
        is_active=True,
        title=body.title,
        skills=body.skills,
        availability="online",
        max_concurrent_tickets=body.max_concurrent_tickets,
    )
    db.add(agent)
    db.flush()
    db.refresh(agent)
    AuditService(db).record(actor_id=current.id, actor_email=current.user.email, action="agent.create",
                            resource_type="agent", resource_id=str(agent.id), request=request)
    db.commit()
    return _serialize_agent(agent, agent)


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(
    agent_id: UUID,
    body: AgentUpdate,
    current: Annotated[CurrentUser, Depends(require_permission(AGENTS_UPDATE))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    user = db.get(User, str(agent_id))
    if user is None:
        raise HTTPException(404, "Agent not found")
    updates = body.model_dump(exclude_unset=True)
    if "full_name" in updates:
        user.full_name = updates["full_name"]
    if "role" in updates:
        user.role = updates["role"]
    if "is_active" in updates:
        user.is_active = updates["is_active"]
    agent = db.get(Agent, str(agent_id))
    if agent is not None:
        for f in ("title", "availability", "max_concurrent_tickets"):
            if f in updates:
                setattr(agent, f, updates[f])
        if "skills" in updates:
            agent.skills = updates["skills"]
    AuditService(db).record(actor_id=current.id, actor_email=current.user.email, action="agent.update",
                            resource_type="agent", resource_id=str(agent_id), metadata=updates, request=request)
    db.commit()
    db.refresh(user)
    return _serialize_agent(user, db.get(Agent, str(user.id)))


@router.post("/{agent_id}/deactivate", response_model=AgentOut)
def deactivate_agent(
    agent_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(AGENTS_DEACTIVATE))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    user = db.get(User, str(agent_id))
    if user is None:
        raise HTTPException(404, "Agent not found")
    user.is_active = False
    AuditService(db).record(actor_id=current.id, actor_email=current.user.email, action="agent.deactivate",
                            resource_type="agent", resource_id=agent_id, request=request)
    db.commit()
    db.refresh(user)
    return _serialize_agent(user, db.get(Agent, str(user.id)))
