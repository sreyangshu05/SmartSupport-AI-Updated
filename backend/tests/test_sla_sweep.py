"""Regression tests for SLAService.sweep_expired() proactive evaluation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.enums import SLABreachStatus, SLAType, TicketPriority, TicketStatus
from app.models.ticket import Ticket, TicketSLA


def _mk_ticket(ticket_number: str, priority: TicketPriority, status: TicketStatus) -> Ticket:
    return Ticket(
        ticket_number=ticket_number,
        subject="sla sweep",
        description="proactive evaluation test",
        status=status,
        priority=priority,
        sla_status=SLABreachStatus.GREEN,
        created_by_email="cust@example.com",
    )


def test_sweep_expired_detects_breach_past_due(db_session):
    """An open ticket whose first-response SLA is past due gets flagged breached."""
    from app.services.sla_service import SLAService

    svc = SLAService(db_session)
    t = _mk_ticket("SLA-1", TicketPriority.HIGH, TicketStatus.OPEN)
    db_session.add(t)
    db_session.commit()

    # Create an SLA record whose start is far in the past (past target).
    past = datetime.now(timezone.utc) - timedelta(hours=2)
    sla = TicketSLA(
        ticket_id=t.id,
        sla_type=SLAType.FIRST_RESPONSE,
        target_minutes=15,   # target 15 min; 2h elapsed => breach
        start_at=past,
        due_at=past + timedelta(minutes=15),
        status=SLABreachStatus.GREEN,
    )
    db_session.add(sla)
    db_session.commit()

    counts = svc.sweep_expired()

    assert counts["evaluated"] == 1
    assert counts["breached"] == 1
    assert counts["warning"] == 0

    db_session.commit()  # evaluate() mutates in-memory; caller commits
    db_session.refresh(t)
    assert t.sla_status == SLABreachStatus.BREACHED


def test_sweep_expired_skips_resolved_tickets(db_session):
    """Closed tickets are not evaluated by the sweep (status filter)."""
    from app.services.sla_service import SLAService

    svc = SLAService(db_session)
    resolved = _mk_ticket("SLA-RES", TicketPriority.URGENT, TicketStatus.CLOSED)
    db_session.add(resolved)
    db_session.commit()

    counts = svc.sweep_expired()
    assert counts["evaluated"] == 0
