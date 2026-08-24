"""Ticket routes. All endpoints enforce server-side permissions."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.ai.base import AINotConfigured, AIProviderError
from app.ai.service import TicketAIService
from app.auth.deps import CurrentUser, require_permission
from app.auth.permissions import (
    TICKETS_ASSIGN,
    TICKETS_CLOSE,
    TICKETS_CREATE,
    TICKETS_MERGE,
    TICKETS_READ,
    TICKETS_REPLY,
    TICKETS_UPDATE,
)
from app.core.database import get_db
from app.models.enums import TicketPriority, TicketStatus, sval
from app.models.kb import TicketKBSuggestion
from app.models.ticket import (
    Ticket,
    TicketEvent,
    TicketResponse,
    TicketTag,
)
from app.models.user import User
from app.schemas.ticket import (
    ClassificationOut,
    DraftReplyOut,
    KBSuggestionOut,
    PagedTickets,
    SimilarTicketOut,
    SummaryOut,
    TicketCreate,
    TicketDetail,
    TicketOut,
    TicketResponseCreate,
    TicketResponseOut,
    TicketUpdate,
)
from app.services.audit_service import AuditService
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _serialize(ticket: Ticket, db: Session, detail: bool = False) -> dict:
    category = ticket.category
    agent = None
    if ticket.assigned_to:
        u = db.get(User, ticket.assigned_to)
        if u:
            agent = {"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": sval(u.role)}
    customer = None
    if ticket.customer_id:
        from app.models.ticket import Customer
        c = db.get(Customer, ticket.customer_id)
        if c:
            customer = {"id": str(c.id), "email": c.email, "full_name": c.full_name, "tier": c.tier}

    base = {
        "id": str(ticket.id),
        "ticket_number": ticket.ticket_number,
        "subject": ticket.subject,
        "description": ticket.description,
        "summary": ticket.summary,
        "status": sval(ticket.status) if hasattr(ticket.status, "value") else ticket.status,
        "priority": sval(ticket.priority) if hasattr(ticket.priority, "value") else ticket.priority,
        "category": {"id": str(category.id), "name": category.name, "description": category.description, "color": category.color}
        if category else None,
        "assigned_agent": agent,
        "created_by_email": ticket.created_by_email,
        "customer": customer,
        "created_at": ticket.created_at,
        "updated_at": ticket.updated_at,
        "resolved_at": ticket.resolved_at,
        "closed_at": ticket.closed_at,
        "sla_status": sval(ticket.sla_status) if hasattr(ticket.sla_status, "value") else ticket.sla_status,
        "sla_due_at": ticket.due_at,
    }
    if detail:
        responses = []
        for r in ticket.assignments or []:
            r_author = db.get(User, r.author_id) if r.author_id else None
            responses.append({
                "id": str(r.id),
                "ticket_id": str(r.ticket_id),
                "content": r.content,
                "response_type": sval(r.response_type) if hasattr(r.response_type, "value") else r.response_type,
                "is_internal": r.is_internal,
                "created_at": r.created_at,
                "author_name": r_author.full_name if r_author else None,
                "author_role": sval(r_author.role) if r_author else None,
            })
        events = [{
            "id": str(e.id),
            "event_type": sval(e.event_type) if hasattr(e.event_type, "value") else e.event_type,
            "old_value": e.old_value,
            "new_value": e.new_value,
            "metadata_json": e.metadata_json,
            "created_at": e.created_at,
        } for e in (ticket.events or [])]
        tags = [t.tag for t in db.query(TicketTag).filter(TicketTag.ticket_id == ticket.id).all()]
        base["responses"] = responses
        base["events"] = events
        base["tags"] = tags
    return base


@router.get("", response_model=PagedTickets)
def list_tickets(
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_READ))],
    db: Annotated[Session, Depends(get_db)],
    search: str | None = None,
    status: TicketStatus | None = None,
    priority: TicketPriority | None = None,
    category_id: str | None = None,
    assigned_to: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    sort: str = Query("newest"),
):
    svc = TicketService(db)
    result = svc.list_tickets(
        current,
        search=search,
        status=status,
        priority=priority,
        category_id=category_id,
        assigned_to=assigned_to,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return {
        "items": [_serialize(t, db) for t in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "pages": result["pages"],
    }


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(
    body: TicketCreate,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_CREATE))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    svc = TicketService(db)
    ticket = svc.create_ticket(
        current,
        subject=body.subject,
        description=body.description,
        priority=body.priority,
        category_id=body.category_id,
        customer_email=body.customer_email,
        customer_name=body.customer_name,
        tags=body.tags,
    )
    AuditService(db).record(
        actor_id=current.id, actor_email=current.user.email,
        action="ticket.create", resource_type="ticket",
        resource_id=str(ticket.id),
        metadata={"ticket_number": ticket.ticket_number},
        request=request,
    )
    AuditService(db).commit()
    # Best-effort: index the ticket for vector similarity search. No-op when
    # AI isn't configured or pgvector isn't present (degrades gracefully).
    TicketAIService().embed_ticket(ticket)
    return _serialize(ticket, db)


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(
    ticket_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    svc = TicketService(db)
    ticket = svc.get_ticket(ticket_id, current)
    return _serialize(ticket, db, detail=True)


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: str,
    body: TicketUpdate,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_UPDATE))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    svc = TicketService(db)
    updates = body.model_dump(exclude_unset=True)
    ticket = svc.update_ticket(
        ticket_id, current,
        subject=updates.get("subject"),
        description=updates.get("description"),
        status=updates.get("status"),
        priority=updates.get("priority"),
        category_id=updates.get("category_id"),
        assigned_to=updates.get("assigned_to"),
    )
    AuditService(db).record(
        actor_id=current.id, actor_email=current.user.email,
        action="ticket.update", resource_type="ticket",
        resource_id=str(ticket.id), metadata=updates, request=request,
    )
    AuditService(db).commit()
    # Re-index when text fields may have changed (best-effort).
    if updates.get("subject") is not None or updates.get("description") is not None:
        TicketAIService().embed_ticket(ticket)
    return _serialize(ticket, db)


@router.post("/{ticket_id}/assign", response_model=TicketOut)
def assign_ticket(
    ticket_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_ASSIGN))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    agent_id: str = Query(description="Agent user id to assign"),
):
    svc = TicketService(db)
    ticket = svc.update_ticket(
        ticket_id, current,
        assigned_to=agent_id, subject=None, description=None,
        status=None, priority=None, category_id=None,
    )
    AuditService(db).record(
        actor_id=current.id, actor_email=current.user.email,
        action="ticket.assign", resource_type="ticket",
        resource_id=str(ticket.id), metadata={"assigned_to": agent_id}, request=request,
    )
    AuditService(db).commit()
    return _serialize(ticket, db)


@router.post("/{ticket_id}/close", response_model=TicketOut)
def close_ticket(
    ticket_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_CLOSE))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    svc = TicketService(db)
    ticket = svc.close_ticket(ticket_id, current)
    AuditService(db).record(
        actor_id=current.id, actor_email=current.user.email,
        action="ticket.close", resource_type="ticket",
        resource_id=str(ticket.id), request=request,
    )
    AuditService(db).commit()
    return _serialize(ticket, db)


@router.post("/{ticket_id}/mark-duplicate")
def mark_duplicate(
    ticket_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_MERGE))],
    db: Annotated[Session, Depends(get_db)],
    duplicate_of: str = Query(description="Ticket id this is a duplicate of"),
):
    svc = TicketService(db)
    ticket = svc.get_ticket(ticket_id, current)
    ticket.is_duplicate_of = duplicate_of
    db.commit()
    return {"ok": True, "ticket_id": str(ticket.id), "duplicate_of": duplicate_of}


@router.post("/{ticket_id}/responses", response_model=TicketResponseOut, status_code=201)
def add_response(
    ticket_id: str,
    body: TicketResponseCreate,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_REPLY))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    svc = TicketService(db)
    resp = svc.add_response(ticket_id, current, content=body.content, is_internal=body.is_internal)
    AuditService(db).record(
        actor_id=current.id, actor_email=current.user.email,
        action="ticket.internal_note" if body.is_internal else "ticket.response",
        resource_type="ticket", resource_id=ticket_id, request=request,
    )
    AuditService(db).commit()
    author = db.get(User, resp.author_id)
    return {
        "id": str(resp.id), "ticket_id": str(resp.ticket_id),
        "content": resp.content,
        "response_type": sval(resp.response_type),
        "is_internal": resp.is_internal, "created_at": resp.created_at,
        "author_name": author.full_name if author else None,
        "author_role": sval(author.role) if author else None,
    }


@router.get("/{ticket_id}/events")
def ticket_events(
    ticket_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    svc = TicketService(db)
    svc.get_ticket(ticket_id, current)
    events = db.query(TicketEvent).filter(TicketEvent.ticket_id == ticket_id).order_by(TicketEvent.created_at.asc()).all()
    return [{
        "id": str(e.id),
        "event_type": sval(e.event_type) if hasattr(e.event_type, "value") else e.event_type,
        "actor_id": e.actor_id, "old_value": e.old_value, "new_value": e.new_value,
        "metadata_json": e.metadata_json, "created_at": e.created_at,
    } for e in events]


@router.get("/{ticket_id}/similar", response_model=list[SimilarTicketOut])
def similar_tickets(
    ticket_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    svc = TicketService(db)
    ticket = svc.get_ticket(ticket_id, current)
    try:
        ais = TicketAIService()
        if not ais.configured:
            return []
        results = ais.similar_tickets(db, ticket)
        return [{"ticket": _serialize(r["ticket"], db), "similarity_score": r["score"]} for r in results]
    except AINotConfigured:
        return []


@router.get("/{ticket_id}/kb-suggestions", response_model=list[KBSuggestionOut])
def kb_suggestions(
    ticket_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    svc = TicketService(db)
    ticket = svc.get_ticket(ticket_id, current)
    # Check persisted suggestions first.
    persisted = db.query(TicketKBSuggestion).filter(TicketKBSuggestion.ticket_id == ticket_id).all()
    if persisted:
        from app.models.kb import KBArticle
        out = []
        for s in persisted:
            art = db.get(KBArticle, s.article_id)
            if art:
                out.append({"article": {"id": str(art.id), "title": art.title, "summary": art.summary},
                            "relevance_score": s.relevance_score, "reason": None})
        return out
    # Generate via AI/retrieval.
    try:
        ais = TicketAIService()
        if not ais.configured:
            raise AINotConfigured()
        retrieved = ais._retrieve_kb(db, ticket)
        return [{"article": {"id": str(art.id), "title": art.title, "summary": art.summary},
                 "relevance_score": round(score, 3), "reason": None} for art, score in retrieved]
    except AINotConfigured:
        return []


@router.post("/{ticket_id}/ai/summary", response_model=SummaryOut)
def ai_summary(
    ticket_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    svc = TicketService(db)
    ticket = svc.get_ticket(ticket_id, current)
    try:
        ais = TicketAIService()
        result = ais.summarize(db, ticket)
        return {"summary": result["summary"], "model": result.get("model"), "sources": []}
    except AINotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc) or "AI is not configured")
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/{ticket_id}/ai/classify", response_model=ClassificationOut)
def ai_classify(
    ticket_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    svc = TicketService(db)
    ticket = svc.get_ticket(ticket_id, current)
    try:
        ais = TicketAIService()
        result = ais.classify(db, ticket)
        from app.models.ticket import TicketCategory
        cat = None
        if result.get("category_id"):
            c = db.get(TicketCategory, result["category_id"])
            if c:
                cat = {"id": str(c.id), "name": c.name, "description": c.description, "color": c.color}
        return {
            "category": cat,
            "category_id": result.get("category_id"),
            "confidence": result.get("confidence", 0.0),
            "low_confidence": result.get("low_confidence", True),
            "reasoning": result.get("reasoning"),
            "model": result.get("model"),
        }
    except AINotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc) or "AI is not configured")
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/{ticket_id}/ai/draft", response_model=DraftReplyOut)
def ai_draft(
    ticket_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(TICKETS_REPLY))],
    db: Annotated[Session, Depends(get_db)],
    force: bool = Query(False),
):
    svc = TicketService(db)
    ticket = svc.get_ticket(ticket_id, current)
    try:
        ais = TicketAIService()
        result = ais.draft_reply(db, ticket, customer_name=None)
        sources = [{"id": "", "title": s, "summary": None} for s in result["sources"]]
        return {"draft": result["draft"], "model": result.get("model"), "sources": sources}
    except AINotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc) or "AI is not configured")
    except AIProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
