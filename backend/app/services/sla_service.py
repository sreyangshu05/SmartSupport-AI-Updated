"""SLA service: creates, tracks, and evaluates SLA records per ticket.

SLA targets are read from ``sla_policies`` when present and fall back to
sensible defaults when none are configured (e.g. fresh environments before
admin setup). Evaluation is deterministic from wall-clock time against each
record's due_at / warning_minutes — no mock values.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import (
    SLABreachStatus,
    SLAType,
    TicketPriority,
    sval,
)
from app.models.ticket import SLAPolicy, Ticket, TicketSLA
from app.models.user import User

# Default SLA targets (minutes) per priority when no SLAPolicy row exists.
# These match typical support contracts and are deliberately explicit.
DEFAULT_SLA_POLICIES: dict[TicketPriority, dict[SLAType, tuple[int, int]]] = {
    TicketPriority.URGENT: {
        SLAType.FIRST_RESPONSE: (15, 10),   # (target, warning)
        SLAType.RESOLUTION: (240, 180),
    },
    TicketPriority.HIGH: {
        SLAType.FIRST_RESPONSE: (60, 45),
        SLAType.RESOLUTION: (480, 360),
    },
    TicketPriority.MEDIUM: {
        SLAType.FIRST_RESPONSE: (240, 180),
        SLAType.RESOLUTION: (1440, 1080),
    },
    TicketPriority.LOW: {
        SLAType.FIRST_RESPONSE: (480, 360),
        SLAType.RESOLUTION: (2880, 2160),
    },
}

class SLAService:
    def __init__(self, db: Session):
        self.db = db

    # -- policies ------------------------------------------------------------
    def _policy_for(
        self, priority: TicketPriority, sla_type: SLAType
    ) -> tuple[int, int] | None:
        """Return configured policy (target, warning) if one exists."""
        row = self.db.scalar(
            select(SLAPolicy).where(
                SLAPolicy.priority == sval(priority),
                SLAPolicy.sla_type == sla_type,
            )
        )
        if row is not None:
            return row.target_minutes, row.warning_minutes
        return None

    def _targets_for(
        self, priority: TicketPriority, sla_type: SLAType
    ) -> tuple[int, int]:
        """Return configured or default (target, warning) minutes."""
        configured = self._policy_for(priority, sla_type)
        if configured is not None:
            return configured
        default = DEFAULT_SLA_POLICIES.get(priority, DEFAULT_SLA_POLICIES[TicketPriority.MEDIUM])
        return default[sla_type]

    def _warning_minutes(self, ticket: Ticket, sla: TicketSLA) -> int:
        """Determine the warning threshold for an SLA record (before breach).

        Prefers the configured policy's ``warning_minutes``; falls back to a
        75% of target heuristic when no policy is configured.
        """
        policy = self.db.scalar(
            select(SLAPolicy).where(
                SLAPolicy.priority == ticket.priority,
                SLAPolicy.sla_type == sla.sla_type,
            )
        )
        if policy is not None:
            return policy.warning_minutes
        return max(1, int(sla.target_minutes * 0.75))

    # -- creation ------------------------------------------------------------
    def create_for_ticket(self, ticket: Ticket) -> None:
        """Create first-response + resolution SLA records for a new ticket."""
        for sla_type in (SLAType.FIRST_RESPONSE, SLAType.RESOLUTION):
            existing = self.db.scalar(
                select(TicketSLA).where(
                    TicketSLA.ticket_id == ticket.id,
                    TicketSLA.sla_type == sla_type,
                )
            )
            if existing is not None:
                continue
            target, warning = self._targets_for(ticket.priority, sla_type)
            now = datetime.now(timezone.utc)
            self.db.add(
                TicketSLA(
                    ticket_id=ticket.id,
                    sla_type=sla_type,
                    target_minutes=target,
                    start_at=now,
                    due_at=now + timedelta(minutes=target),
                    status=SLABreachStatus.GREEN,
                )
            )
        # Surface the tightest due time on the ticket for dashboard visibility.
        first = self.db.scalar(
            select(TicketSLA).where(
                TicketSLA.ticket_id == ticket.id,
                TicketSLA.sla_type == SLAType.FIRST_RESPONSE,
            )
        )
        if first is not None:
            ticket.due_at = first.due_at

    # -- resolution ----------------------------------------------------------
    def resolve_first_response(self, ticket: Ticket) -> None:
        now = datetime.now(timezone.utc)
        sla = self.db.scalar(
            select(TicketSLA).where(
                TicketSLA.ticket_id == ticket.id,
                TicketSLA.sla_type == SLAType.FIRST_RESPONSE,
            )
        )
        if sla is not None and sla.resolved_at is None:
            sla.resolved_at = now
            sla.status = SLABreachStatus.GREEN

    def resolve_resolution(self, ticket: Ticket) -> None:
        now = datetime.now(timezone.utc)
        sla = self.db.scalar(
            select(TicketSLA).where(
                TicketSLA.ticket_id == ticket.id,
                TicketSLA.sla_type == SLAType.RESOLUTION,
            )
        )
        if sla is not None and sla.resolved_at is None:
            sla.resolved_at = now
            sla.status = SLABreachStatus.GREEN

    # -- evaluation ----------------------------------------------------------
    def evaluate(self, ticket: Ticket) -> SLABreachStatus:
        """Recompute sla_status from each SLA record's timing.

        Returns the worst state across open SLA records (breached > warning >
        green). Resolved SLA records are ignored because they already achieved
        their target.
        """
        now = datetime.now(timezone.utc)
        slas = list(
            self.db.scalars(
                select(TicketSLA).where(TicketSLA.ticket_id == ticket.id)
            )
        )

        # Fall back to green if no records (shouldn't happen once wired).
        if not slas:
            return SLABreachStatus.GREEN

        severity_rank = {
            sval(SLABreachStatus.GREEN): 0,
            sval(SLABreachStatus.WARNING): 1,
            sval(SLABreachStatus.BREACHED): 2,
        }
        worst_rank = 0
        for sla in slas:
            if sla.resolved_at is not None:
                continue  # resolved SLA keeps green
            previous = sla.status if sla.status is not None else SLABreachStatus.GREEN
            state: SLABreachStatus
            if previous == SLABreachStatus.BREACHED:
                state = SLABreachStatus.BREACHED
            else:
                minutes = (now - sla.start_at).total_seconds() / 60.0
                if minutes >= sla.target_minutes:
                    state = SLABreachStatus.BREACHED
                elif minutes >= self._warning_minutes(ticket, sla):
                    state = SLABreachStatus.WARNING
                else:
                    state = SLABreachStatus.GREEN
            if state != previous:
                sla.status = state
                # Fire a notification on degradation transitions only.
                self._notify_sla_transition(ticket, sla.sla_type, state, previous)
            elif sla.status is None:
                sla.status = state
            worst_rank = max(worst_rank, severity_rank[sval(state)])

        if worst_rank >= 2:
            result = SLABreachStatus.BREACHED
        elif worst_rank == 1:
            result = SLABreachStatus.WARNING
        else:
            result = SLABreachStatus.GREEN
        ticket.sla_status = result
        return result

    def sweep_expired(self) -> dict:
        """Proactively evaluate SLA state for all open tickets.

        Read-time evaluation only advances SLA state when a ticket is fetched,
        so a quiet ticket could sit labelled green past its breach point. This
        sweep walks every open ticket and forces ``evaluate()`` so warning/
        breach transitions are detected and notified even with no one looking.
        It is idempotent (evaluate() only writes on state change) and safe to
        call from a scheduler, cron, or an on-demand admin trigger.
        """
        open_tickets = list(
            self.db.scalars(
                select(Ticket).where(
                    Ticket.status.in_(["open", "in_progress"])
                )
            )
        )
        counts = {"evaluated": 0, "warning": 0, "breached": 0}
        for t in open_tickets:
            state = self.evaluate(t)
            counts["evaluated"] += 1
            if state == SLABreachStatus.WARNING:
                counts["warning"] += 1
            elif state == SLABreachStatus.BREACHED:
                counts["breached"] += 1
        return counts

    def _notify_sla_transition(
        self, ticket: Ticket, sla_type: SLAType, state: SLABreachStatus, previous: SLABreachStatus
    ) -> None:
        """Notify admins when a ticket's SLA state degrades (warning/breach)."""
        if state in (SLABreachStatus.WARNING, SLABreachStatus.BREACHED):
            label = "SLA warning" if state == SLABreachStatus.WARNING else "SLA breach"
            kind = f"sla.{sval(state)}" if state == SLABreachStatus.WARNING else "sla.breach"
            ticket_no = getattr(ticket, "ticket_number", "ticket")
            admins = self.db.scalars(
                select(User).where(User.is_active.is_(True), User.role == "admin")
            ).all()
            from app.services.notification_service import NotificationService
            for admin in admins:
                NotificationService(self.db).record(
                    user_id=str(admin.id),
                    type=kind,
                    title=f"{label}: {ticket_no}",
                    message=f"{sval(sla_type).replace('_', ' ')} target at risk for {ticket_no}",
                    link=f"/tickets/{ticket.id}",
                )
