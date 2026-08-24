"""Analytics derived from persisted data — never mock."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import TicketStatus, sval
from app.models.ticket import Ticket, TicketResponse
from app.models.user import User

# Severity of status counted as "open-ish" for workload metrics.
ACTIVE_STATUSES = (
    TicketStatus.OPEN,
    TicketStatus.IN_PROGRESS,
    TicketStatus.WAITING_FOR_CUSTOMER,
    TicketStatus.WAITING_FOR_INTERNAL,
)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def _range(self, start: datetime | None, end: datetime | None):
        start = start or (datetime.now(timezone.utc) - timedelta(days=30))
        end = end or datetime.now(timezone.utc)
        if start > end:
            start, end = end, start
        return start, end

    def overview(self, start: datetime | None = None, end: datetime | None = None) -> dict:
        s, e = self._range(start, end)
        base = select(Ticket).where(Ticket.created_at >= s, Ticket.created_at <= e)

        total = self.db.scalar(
            select(func.count()).select_from(base.subquery())
        ) or 0
        open_count = self.db.scalar(
            select(func.count()).where(
                Ticket.status.in_(ACTIVE_STATUSES), Ticket.created_at >= s, Ticket.created_at <= e
            )
        ) or 0
        in_progress = self.db.scalar(
            select(func.count()).where(
                Ticket.status == TicketStatus.IN_PROGRESS,
                Ticket.created_at >= s, Ticket.created_at <= e,
            )
        ) or 0
        resolved = self.db.scalar(
            select(func.count()).where(
                Ticket.status.in_((TicketStatus.RESOLVED, TicketStatus.CLOSED)),
                Ticket.created_at >= s, Ticket.created_at <= e,
            )
        ) or 0

        # Average resolution time among resolved tickets in range.
        tickets = self.db.scalars(
            select(Ticket).where(
                Ticket.resolved_at.isnot(None),
                Ticket.created_at >= s, Ticket.created_at <= e,
            ).limit(1000)
        ).all()
        res_times = [
            (t.resolved_at - t.created_at).total_seconds() / 60.0
            for t in tickets if t.resolved_at and t.created_at
        ]
        avg_res = round(sum(res_times) / len(res_times), 1) if res_times else None

        # First response timing.
        fr_resp = self.db.scalars(
            select(Ticket).where(
                Ticket.first_response_at.isnot(None),
                Ticket.created_at >= s, Ticket.created_at <= e,
            ).limit(1000)
        ).all()
        fr_times = [
            (t.first_response_at - t.created_at).total_seconds() / 60.0
            for t in fr_resp if t.first_response_at and t.created_at
        ]
        avg_fr = round(sum(fr_times) / len(fr_times), 1) if fr_times else None

        # SLA compliance (green vs breached among resolved, rough).
        slas = [t for t in tickets if t.sla_status is not None]
        compliance = (
            round(
                sum(1 for t in slas if sval(t.sla_status) == "green") / len(slas) * 100,
                1,
            )
            if slas
            else None
        )

        return {
            "total_tickets": total,
            "open_tickets": open_count,
            "in_progress_tickets": in_progress,
            "resolved_tickets": resolved,
            "avg_resolution_minutes": avg_res,
            "avg_first_response_minutes": avg_fr,
            "sla_compliance_rate": compliance,
            "tickets_by_status": self._count_by(Ticket.status, s, e),
            "tickets_by_priority": self._count_by(Ticket.priority, s, e),
            "tickets_by_category": self._count_category(s, e),
            "top_agents": self._top_agents(s, e),
        }

    def _count_by(self, column, s, e) -> dict[str, int]:
        rows = self.db.execute(
            select(column, func.count()).where(
                Ticket.created_at >= s, Ticket.created_at <= e
            ).group_by(column)
        ).all()
        return {str(k): int(v) for k, v in rows}

    def _count_category(self, s, e) -> dict[str, int]:
        rows = self.db.execute(
            select(Ticket.category_id, func.count()).where(
                Ticket.created_at >= s, Ticket.created_at <= e
            ).group_by(Ticket.category_id)
        ).all()
        from app.models.ticket import TicketCategory

        names = {
            c.id: c.name for c in self.db.scalars(select(TicketCategory)).all()
        }
        return {names.get(k, "Uncategorized"): int(v) for k, v in rows}

    def _top_agents(self, s, e) -> list[dict]:
        rows = self.db.execute(
            select(
                TicketResponse.author_id,
                func.count(TicketResponse.id),
            )
            .where(
                TicketResponse.created_at >= s,
                TicketResponse.created_at <= e,
                TicketResponse.is_internal.is_(False),
            )
            .group_by(TicketResponse.author_id)
            .order_by(func.count(TicketResponse.id).desc())
            .limit(5)
        ).all()
        result = []
        for author_id, count in rows:
            user = self.db.get(User, author_id) if author_id else None
            result.append(
                {
                    "agent_id": author_id,
                    "agent_name": user.full_name if user else "Unknown",
                    "responses": count,
                }
            )
        return result

    def agent_performance(self) -> list[dict]:
        users = self.db.scalars(select(User).where(User.is_active.is_(True))).all()
        out = []
        for u in users:
            resolved = self.db.scalar(
                select(func.count()).where(
                    Ticket.assigned_to == str(u.id),
                    Ticket.status.in_((TicketStatus.RESOLVED, TicketStatus.CLOSED)),
                )
            ) or 0
            created = self.db.scalar(
                select(func.count()).where(Ticket.assigned_to == str(u.id))
            ) or 0
            responses = self.db.scalar(
                select(func.count()).where(TicketResponse.author_id == str(u.id))
            ) or 0
            open_load = self.db.scalar(
                select(func.count()).where(
                    Ticket.assigned_to == str(u.id), Ticket.status.in_(ACTIVE_STATUSES)
                )
            ) or 0
            out.append(
                {
                    "agent_id": str(u.id),
                    "agent_name": u.full_name,
                    "tickets_resolved": resolved,
                    "tickets_created": created,
                    "total_responses": responses,
                    "open_tickets": open_load,
                }
            )
        out.sort(key=lambda x: x["tickets_resolved"], reverse=True)
        return out
