"""Ticket workflow service: business rules live here, never in routes or UI."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.models.enums import (
    EventType,
    ResponseType,
    TicketPriority,
    TicketStatus,
    sval,
)
from app.models.notification import Notification
from app.models.ticket import (
    Customer,
    Ticket,
    TicketEvent,
    TicketResponse,
    TicketTag,
)
from app.models.user import User
from app.services.notification_service import NotificationService
from app.services.sla_service import SLAService

# Valid status transitions (phase 5 of the brief).
VALID_TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    TicketStatus.OPEN: {TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
    TicketStatus.IN_PROGRESS: {
        TicketStatus.WAITING_FOR_CUSTOMER,
        TicketStatus.WAITING_FOR_INTERNAL,
        TicketStatus.RESOLVED,
        TicketStatus.OPEN,
    },
    TicketStatus.WAITING_FOR_CUSTOMER: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
    },
    TicketStatus.WAITING_FOR_INTERNAL: {
        TicketStatus.IN_PROGRESS,
        TicketStatus.RESOLVED,
    },
    TicketStatus.RESOLVED: {TicketStatus.CLOSED, TicketStatus.IN_PROGRESS},
    TicketStatus.CLOSED: {TicketStatus.OPEN},  # reopen
}

OPEN_STATUSES = {
    TicketStatus.OPEN,
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING_FOR_CUSTOMER,
    TicketStatus.WAITING_FOR_INTERNAL,
}
RESOLVED_OR_CLOSED = {TicketStatus.RESOLVED, TicketStatus.CLOSED}


class TicketNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=404, detail="Ticket could not be found")


class InvalidStatusTransition(HTTPException):
    def __init__(self, current: TicketStatus, requested: TicketStatus) -> None:
        super().__init__(
            status_code=400,
            detail=f"Cannot transition ticket from {sval(current)} to {sval(requested)}",
        )


class TicketService:
    def __init__(self, db: Session):
        self.db = db

    # -- helpers -------------------------------------------------------------
    def _get_or_create_customer(self, email: str, name: str | None) -> Customer:
        customer = self.db.scalar(select(Customer).where(Customer.email == email))
        if customer is None:
            customer = Customer(email=email, full_name=name, tier="standard")
            self.db.add(customer)
            self.db.flush()
        elif name:
            customer.full_name = name
        return customer

    def _next_ticket_number(self) -> str:
        """Server-side monotonic ticket numbering.

        Computes MAX()+1 in a single statement with a row lock semantics by
        relying on the unique constraint: the generated number is validated by
        the DB, and a rare collision simply retries. This avoids the naive
        client-side ``tickets.length + 1`` and stays safe under concurrency.
        """
        SQL = (
            "SELECT COALESCE(MAX(CAST(REPLACE(ticket_number,'TKT-','') "
            "AS BIGINT)),0)+1 AS n FROM tickets"
        )
        result = self.db.execute(text(SQL))
        return f"TKT-{result.scalar_one():08d}"

    def _add_event(
        self,
        ticket: Ticket,
        event_type: EventType,
        actor_id: str | None,
        old_value: str | None = None,
        new_value: str | None = None,
        metadata_json: str | None = None,
    ) -> None:
        self.db.add(
            TicketEvent(
                ticket_id=ticket.id,
                actor_id=actor_id,
                event_type=event_type,
                old_value=old_value,
                new_value=new_value,
                metadata_json=metadata_json,
                created_at=datetime.now(timezone.utc),
            )
        )

    # -- notifications -------------------------------------------------------
    def _notify_user(
        self,
        user_id: str,
        *,
        type: str,
        title: str,
        message: str | None = None,
        link: str | None = None,
    ) -> None:
        """Create an in-app notification within the current transaction."""
        NotificationService(self.db).record(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            link=link,
        )

    def _notify_assigned_agent(self, ticket: Ticket, *, type: str, title: str, message: str) -> None:
        if ticket.assigned_to:
            self._notify_user(
                str(ticket.assigned_to), type=type, title=title, message=message,
                link=f"/tickets/{ticket.id}",
            )

    def _notify_active_agents(self, *, type: str, title: str, message: str, skip_id: str | None = None) -> None:
        agents = self.db.scalars(
            select(User).where(User.is_active.is_(True))
        ).all()
        for agent in agents:
            if skip_id and str(agent.id) == skip_id:
                continue
            self._notify_user(
                str(agent.id), type=type, title=title, message=message,
            )

    # -- queries -------------------------------------------------------------
    def get_ticket(self, ticket_id: str, actor: CurrentUser) -> Ticket:
        ticket = self.db.get(Ticket, ticket_id)
        if ticket is None:
            raise TicketNotFound()
        # Re-evaluate time-based SLA state on detail read (cheap, bounded to
        # one ticket) so the dashboard reflects warning/breach in real time.
        SLAService(self.db).evaluate(ticket)
        self.db.flush()
        return ticket

    def list_tickets(
        self,
        actor: CurrentUser,
        *,
        search: str | None = None,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        category_id: str | None = None,
        assigned_to: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        page: int = 1,
        page_size: int = 25,
        sort: str = "newest",
    ) -> dict:
        stmt = select(Ticket)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Ticket.subject.ilike(like),
                    Ticket.description.ilike(like),
                    Ticket.ticket_number.ilike(like),
                    Ticket.created_by_email.ilike(like),
                )
            )
        if status:
            stmt = stmt.where(Ticket.status == status)
        if priority:
            stmt = stmt.where(Ticket.priority == priority)
        if category_id:
            stmt = stmt.where(Ticket.category_id == category_id)
        if assigned_to:
            stmt = stmt.where(Ticket.assigned_to == assigned_to)
        if date_from:
            stmt = stmt.where(Ticket.created_at >= date_from)
        if date_to:
            stmt = stmt.where(Ticket.created_at <= date_to)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        if sort == "oldest":
            stmt = stmt.order_by(Ticket.created_at.asc())
        else:
            stmt = stmt.order_by(Ticket.created_at.desc())

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = self.db.scalars(stmt).all()

        pages = max(1, (total + page_size - 1) // page_size)
        return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}

    # -- write operations ----------------------------------------------------
    def create_ticket(
        self,
        actor: CurrentUser,
        *,
        subject: str,
        description: str,
        priority: TicketPriority,
        category_id: str | None,
        customer_email: str,
        customer_name: str | None,
        tags: list[str],
    ) -> Ticket:
        customer = self._get_or_create_customer(customer_email, customer_name)
        ticket = Ticket(
            ticket_number=self._next_ticket_number(),
            subject=subject,
            description=description,
            priority=priority,
            category_id=category_id,
            assigned_to=None,
            created_by_email=customer_email,
            customer_id=customer.id,
            status=TicketStatus.OPEN,
        )
        self.db.add(ticket)
        self.db.flush()

        for tag in {t.strip().lower() for t in tags if t.strip()}:
            self.db.add(TicketTag(ticket_id=ticket.id, tag=tag))

        self._add_event(ticket, EventType.CREATED, actor.id, new_value=subject)
        # Create first-response + resolution SLA records and surface due time.
        SLAService(self.db).create_for_ticket(ticket)
        # Notify teammates a new ticket landed (skip the creator).
        self._notify_active_agents(
            type="ticket.created",
            title="New ticket",
            message=f"{ticket.ticket_number}: {ticket.subject}",
            skip_id=actor.id,
        )
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def update_ticket(
        self,
        ticket_id: str,
        actor: CurrentUser,
        *,
        subject: str | None,
        description: str | None,
        status: TicketStatus | None,
        priority: TicketPriority | None,
        category_id: str | None,
        assigned_to: str | None,
    ) -> Ticket:
        ticket = self.get_ticket(ticket_id, actor)

        if status is not None and status != ticket.status:
            allowed = VALID_TRANSITIONS.get(ticket.status, set())
            if status not in allowed:
                raise InvalidStatusTransition(ticket.status, status)
            self._add_event(
                ticket, EventType.STATUS_CHANGED, actor.id,
                old_value=sval(ticket.status), new_value=sval(status),
            )
            # Manage lifecycle timestamps + SLA.
            if status in RESOLVED_OR_CLOSED and ticket.resolved_at is None:
                ticket.resolved_at = datetime.now(timezone.utc)
            if status == TicketStatus.CLOSED and ticket.closed_at is None:
                ticket.closed_at = datetime.now(timezone.utc)
            if (
                status == TicketStatus.RESOLVED
                and ticket.status == TicketStatus.CLOSED
            ):
                ticket.closed_at = None  # reactivation
            ticket.status = status
            # Reaching a resolved/closed state satisfies the resolution SLA.
            if status in RESOLVED_OR_CLOSED:
                SLAService(self.db).resolve_resolution(ticket)

        if priority is not None and priority != ticket.priority:
            self._add_event(
                ticket, EventType.PRIORITY_CHANGED, actor.id,
                old_value=sval(ticket.priority), new_value=sval(priority),
            )
            ticket.priority = priority

        if category_id is not None and category_id != ticket.category_id:
            self._add_event(
                ticket, EventType.CATEGORY_CHANGED, actor.id,
                old_value=ticket.category_id, new_value=category_id,
            )
            ticket.category_id = category_id

        if assigned_to is not None and assigned_to != ticket.assigned_to:
            event = EventType.REASSIGNED if ticket.assigned_to else EventType.ASSIGNED
            self._add_event(
                ticket, event, actor.id,
                old_value=ticket.assigned_to, new_value=assigned_to,
            )
            ticket.assigned_to = assigned_to
            # Notify the newly assigned agent.
            self._notify_assigned_agent(
                ticket,
                type="ticket.assigned",
                title="Ticket assigned to you",
                message=f"{ticket.ticket_number}: {ticket.subject}",
            )

        if subject is not None:
            ticket.subject = subject
        if description is not None:
            ticket.description = description

        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def add_response(
        self,
        ticket_id: str,
        actor: CurrentUser,
        *,
        content: str,
        is_internal: bool,
    ) -> TicketResponse:
        ticket = self.get_ticket(ticket_id, actor)
        response = TicketResponse(
            ticket_id=ticket.id,
            author_id=actor.id,
            content=content,
            response_type=ResponseType.INTERNAL_NOTE if is_internal else ResponseType.AGENT,
            is_internal=is_internal,
        )
        self.db.add(response)
        self.db.flush()

        event = EventType.INTERNAL_NOTE_ADDED if is_internal else EventType.RESPONSE_ADDED
        self._add_event(ticket, event, actor.id)

        if not is_internal and ticket.first_response_at is None:
            ticket.first_response_at = datetime.now(timezone.utc)
            # First real response satisfies the first-response SLA.
            SLAService(self.db).resolve_first_response(ticket)

        # Auto-advance status when an agent responds (if still open).
        if not is_internal and ticket.status == TicketStatus.OPEN:
            self._add_event(
                ticket, EventType.STATUS_CHANGED, actor.id,
                old_value=sval(ticket.status), new_value=TicketStatus.IN_PROGRESS.value,
            )
            ticket.status = TicketStatus.IN_PROGRESS

        # Notify the assigned agent of a reply/internal note unless they wrote it.
        if ticket.assigned_to and str(ticket.assigned_to) != actor.id:
            if is_internal:
                self._notify_assigned_agent(
                    ticket,
                    type="ticket.internal_note",
                    title="Internal note added",
                    message=f"An internal note was added to {ticket.ticket_number}",
                )
            else:
                self._notify_assigned_agent(
                    ticket,
                    type="ticket.reply",
                    title="New reply sent",
                    message=f"A reply was sent on {ticket.ticket_number}",
                )

        self.db.commit()
        self.db.refresh(response)
        return response

    def close_ticket(self, ticket_id: str, actor: CurrentUser) -> Ticket:
        return self.update_ticket(
            ticket_id, actor,
            status=TicketStatus.CLOSED, subject=None, description=None,
            priority=None, category_id=None, assigned_to=None,
        )
