"""Misc reference-data routes (categories, customers, clusters)."""
from __future__ import annotations

from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser, get_current_user
from app.ai.openai_provider import OpenAICompatProvider
from app.core import vector_store
from app.core.database import engine
from app.core.database import get_db
from app.models.enums import TicketStatus, sval
from app.models.ticket import Customer, Ticket, TicketCategory
from app.models.ai import TicketEmbedding

router = APIRouter(tags=["reference"])

RESOLVED = (TicketStatus.RESOLVED, TicketStatus.CLOSED)


@router.get("/categories")
def list_categories(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    cats = db.scalars(select(TicketCategory).order_by(TicketCategory.name)).all()
    return [{"id": str(c.id), "name": c.name, "description": c.description, "color": c.color} for c in cats]


@router.get("/customers/{customer_id}")
def get_customer(
    customer_id: str,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    c = db.get(Customer, customer_id)
    if c is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Customer not found")
    open_count = db.scalar(select(func.count()).where(
        Ticket.customer_id == customer_id, Ticket.status.in_((
            TicketStatus.OPEN, TicketStatus.IN_PROGRESS,
            TicketStatus.WAITING_FOR_CUSTOMER, TicketStatus.WAITING_FOR_INTERNAL,
        ))
    )) or 0
    resolved_count = db.scalar(select(func.count()).where(
        Ticket.customer_id == customer_id, Ticket.status.in_(RESOLVED)
    )) or 0
    total = db.scalar(select(func.count()).where(Ticket.customer_id == customer_id)) or 0
    recent = db.scalars(
        select(Ticket).where(Ticket.customer_id == customer_id).order_by(Ticket.created_at.desc()).limit(10)
    ).all()
    return {
        "id": str(c.id), "email": c.email, "full_name": c.full_name, "tier": c.tier,
        "open_tickets": open_count, "resolved_tickets": resolved_count, "total_tickets": total,
        "recent_tickets": [
            {
                "id": str(t.id), "ticket_number": t.ticket_number, "subject": t.subject,
                "status": sval(t.status), "priority": sval(t.priority),
                "created_at": t.created_at,
            } for t in recent
        ],
    }


@router.get("/clusters")
def issue_clusters(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Issue clustering derived from persisted ticket embeddings."""
    tickets = db.scalars(select(Ticket)).all()
    if not tickets:
        return []
    provider = OpenAICompatProvider()
    if not provider.is_configured():
        return []
    with engine.connect() as conn:
        if not vector_store.embedding_column_exists(conn, vector_store.TICKET_EMBEDDINGS):
            return []
        rows = conn.execute(
            text(
                "SELECT ticket_id, embedding FROM ticket_embeddings "
                "ORDER BY created_at DESC"
            )
        ).fetchall()
    vectors = {str(row[0]): [float(x) for x in row[1]] for row in rows if row[0] and row[1]}
    if len(vectors) < 2:
        return []

    grouped: set[str] = set()
    groups: list[dict] = []
    ordered = list(vectors.items())
    for base_id, base_vec in ordered:
        if base_id in grouped:
            continue
        base_ticket = next((t for t in tickets if str(t.id) == base_id), None)
        if base_ticket is None:
            continue
        cluster_ids = [base_id]
        for other_id, other_vec in ordered:
            if other_id == base_id or other_id in grouped:
                continue
            # Use cosine similarity via the stored vectors directly.
            dot = sum(a * b for a, b in zip(base_vec, other_vec))
            base_norm = sum(a * a for a in base_vec) ** 0.5
            other_norm = sum(a * a for a in other_vec) ** 0.5
            if base_norm and other_norm and (dot / (base_norm * other_norm)) >= 0.9:
                cluster_ids.append(other_id)
        if len(cluster_ids) >= 2:
            grouped.update(cluster_ids)
            groups.append({
                "id": f"cluster-{len(groups)+1}",
                "name": base_ticket.subject[:40],
                "ticket_count": len(cluster_ids),
                "confidence": 0.9,
                "representative_ticket_ids": cluster_ids[:5],
                "is_trending": len(cluster_ids) >= 3,
            })
    return groups
