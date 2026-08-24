"""Development seed data.

Mirrors the mock data that previously lived client-side into real persistent
records so the demo environment is immediately usable. Run with:

    python -m app.seed

Idempotent: safe to run repeatedly.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models import Base
from app.models.enums import (
    KBArticleStatus,
    ResponseType,
    RoleEnum,
    SLAType,
    TicketPriority,
    TicketStatus,
)
from app.models.kb import KBArticle, KBArticleVersion
from app.models.notification import Notification
from app.models.ticket import (
    Customer,
    Ticket,
    TicketCategory,
    TicketEvent,
    TicketResponse,
    TicketTag,
    SLAPolicy,
)
from app.models.user import User
from app.auth.security import hash_password

settings = get_settings()


def _now(**kw) -> datetime:
    return datetime.now(timezone.utc) - timedelta(**kw)


def seed(db: Session) -> None:
    # -- Categories (from mockCategories) ------------------------------------
    categories_data = [
        ("Technical Issue", "Technical problems and bugs", "#EF4444"),
        ("Billing", "Billing and payment issues", "#10B981"),
        ("Account", "Account management and access", "#3B82F6"),
        ("Feature Request", "New feature requests", "#8B5CF6"),
        ("General Inquiry", "General questions", "#6B7280"),
    ]
    cats: dict[str, TicketCategory] = {}
    for name, desc, color in categories_data:
        existing = db.scalar(select(TicketCategory).where(TicketCategory.name == name))
        if existing:
            cats[name] = existing
            continue
        c = TicketCategory(name=name, description=desc, color=color)
        db.add(c)
        db.flush()
        cats[name] = c

    # -- SLA policies --------------------------------------------------------
    sla_policy_data = [
        ("Urgent First Response", SLAType.FIRST_RESPONSE, TicketPriority.URGENT, 15, 10),
        ("Urgent Resolution", SLAType.RESOLUTION, TicketPriority.URGENT, 240, 180),
        ("High First Response", SLAType.FIRST_RESPONSE, TicketPriority.HIGH, 60, 45),
        ("High Resolution", SLAType.RESOLUTION, TicketPriority.HIGH, 480, 360),
        ("Medium First Response", SLAType.FIRST_RESPONSE, TicketPriority.MEDIUM, 240, 180),
        ("Medium Resolution", SLAType.RESOLUTION, TicketPriority.MEDIUM, 1440, 1080),
        ("Low First Response", SLAType.FIRST_RESPONSE, TicketPriority.LOW, 480, 360),
        ("Low Resolution", SLAType.RESOLUTION, TicketPriority.LOW, 2880, 2160),
    ]
    for name, sla_type, priority, target, warning in sla_policy_data:
        existing = db.scalar(
            select(SLAPolicy).where(
                SLAPolicy.name == name,
                SLAPolicy.sla_type == sla_type,
                SLAPolicy.priority == priority,
            )
        )
        if existing:
            continue
        db.add(
            SLAPolicy(
                name=name,
                sla_type=sla_type,
                priority=priority,
                target_minutes=target,
                warning_minutes=warning,
            )
        )

    # -- Users/agents (from mockAgents) --------------------------------------
    users_data = [
        ("admin@smart.support", "SmartSupport Admin", RoleEnum.ADMIN, settings.SEED_ADMIN_PASSWORD),
        ("john@smart.support", "John Senior", RoleEnum.SENIOR_AGENT, "agent123"),
        ("emma@smart.support", "Emma Wilson", RoleEnum.AGENT, "agent123"),
    ]
    users: dict[str, User] = {}
    for email, name, role, pw in users_data:
        existing = db.scalar(select(User).where(User.email == email))
        if existing:
            users[email] = existing
            continue
        u = User(
            email=email,
            full_name=name,
            role=role,
            password_hash=hash_password(pw),
            is_active=True,
        )
        db.add(u)
        db.flush()
        users[email] = u

    # -- Customers ----------------------------------------------------------
    def get_customer(email: str, name: str | None) -> Customer:
        c = db.scalar(select(Customer).where(Customer.email == email))
        if c is None:
            c = Customer(email=email, full_name=name, tier="standard")
            db.add(c)
            db.flush()
        return c

    # -- Tickets (from mockTickets) -----------------------------------------
    if db.scalar(select(Ticket).limit(1)) is None:
        ticket_seed = [
            {
                "subject": "Password reset link not working",
                "description": "I requested a password reset but the link in my email is not working. When I click it, I get an error saying 'Invalid or expired token'. I tried multiple times.",
                "status": TicketStatus.IN_PROGRESS,
                "priority": TicketPriority.HIGH,
                "cat": "Account",
                "customer": ("customer@example.com", "Alice Customer"),
                "assigned": "john@smart.support",
                "created": _now(days=2),
                "tags": ["password", "login", "security"],
                "summary": "User unable to reset password - link shows invalid token error",
            },
            {
                "subject": "Charged twice for subscription",
                "description": "I was charged twice for my monthly subscription this month. I see two charges of $29.99 on my credit card statement.",
                "status": TicketStatus.OPEN,
                "priority": TicketPriority.URGENT,
                "cat": "Billing",
                "customer": ("usertwo@example.com", "Bob Billing"),
                "assigned": "emma@smart.support",
                "created": _now(days=1),
                "tags": ["billing", "refund"],
                "summary": "Duplicate billing - two charges for single subscription period",
            },
            {
                "subject": "Cannot access dashboard",
                "description": "Getting 403 error when trying to access my dashboard.",
                "status": TicketStatus.RESOLVED,
                "priority": TicketPriority.MEDIUM,
                "cat": "Technical Issue",
                "customer": ("testy@user.com", "Test User"),
                "assigned": "john@smart.support",
                "created": _now(days=5),
                "tags": ["access", "dashboard"],
                "summary": "Access denied error on dashboard",
            },
            {
                "subject": "Feature: dark mode support",
                "description": "Would love a dark mode option for the application. My eyes strain with the current light theme.",
                "status": TicketStatus.OPEN,
                "priority": TicketPriority.LOW,
                "cat": "Feature Request",
                "customer": ("carol@example.com", "Carol Request"),
                "assigned": None,
                "created": _now(hours=6),
                "tags": ["feature", "ui"],
                "summary": "User requests dark mode support",
            },
        ]
        for t in ticket_seed:
            cust = get_customer(t["customer"][0], t["customer"][1])
            cat = cats[t["cat"]]
            assigned = users[t["assigned"]].id if t["assigned"] else None
            ticket = Ticket(
                ticket_number="", subject=t["subject"], description=t["description"],
                summary=t["summary"], status=t["status"], priority=t["priority"],
                category_id=cat.id, assigned_to=assigned,
                created_by_email=t["customer"][0], customer_id=cust.id,
                created_at=t["created"], updated_at=t["created"],
            )
            db.add(ticket)
            db.flush()
            # Assign a monotonic ticket number manually for seeds.
            num = db.execute(select(Ticket.ticket_number)).scalars().all()
            nums = [int(n.split("-")[1]) for n in num if n]
            ticket.ticket_number = f"TKT-{(max(nums)+1 if nums else 1):08d}"
            for tag in t["tags"]:
                db.add(TicketTag(ticket_id=ticket.id, tag=tag))
            # SLA records for the seeded ticket.
            from app.services.sla_service import SLAService
            SLAService(db).create_for_ticket(ticket)
            # A sample agent response on the in-progress ticket.
            if t["status"] == TicketStatus.IN_PROGRESS:
                db.add(TicketResponse(
                    ticket_id=ticket.id, author_id=str(users["john@smart.support"].id),
                    content="I've escalated this to our auth team. Could you try clearing your browser cache and retrying the reset link?",
                    response_type=ResponseType.AGENT, is_internal=False,
                    created_at=t["created"] + timedelta(minutes=30),
                ))
                ticket.first_response_at = t["created"] + timedelta(minutes=30)
            if t["status"] == TicketStatus.RESOLVED:
                db.add(TicketResponse(
                    ticket_id=ticket.id, author_id=str(users["john@smart.support"].id),
                    content="This was resolved — the dashboard access token had expired. You should have access again now.",
                    response_type=ResponseType.AGENT, is_internal=False,
                    created_at=t["created"] + timedelta(hours=20),
                ))
                ticket.resolved_at = t["created"] + timedelta(hours=20)
                ticket.first_response_at = t["created"] + timedelta(hours=1)
            db.add(TicketEvent(
                ticket_id=ticket.id, actor_id=assigned, event_type="created",
                new_value=t["subject"], created_at=t["created"],
            ))

    # -- KB articles (from mockKBArticles) ----------------------------------
    if db.scalar(select(KBArticle).limit(1)) is None:
        kb_seed = [
            ("How to Reset Your Password",
             "# Password Reset Guide\n\n1. Go to the login page\n2. Click 'Forgot Password'\n3. Enter your email\n4. Check your email for reset link\n5. Click the link and create a new password",
             "Step-by-step guide for resetting your password",
             "Account", ["password", "account", "security"]),
            ("Understanding Your Billing Cycle",
             "# Billing Information\n\nYour billing cycle starts on the day you subscribe and renews monthly.",
             "Explanation of billing cycles and charges",
             "Billing", ["billing", "subscription", "payments"]),
            ("Common Dashboard Access Issues",
             "# Dashboard Access\n\nIf you see a 403, your session token may have expired. Log out and log back in.",
             "Troubleshooting dashboard access errors",
             "Technical Issue", ["dashboard", "access", "403"]),
        ]
        for title, content, summary, cat_name, tags in kb_seed:
            art = KBArticle(
                title=title, content=content, summary=summary,
                category_id=cats[cat_name].id, status=KBArticleStatus.PUBLISHED,
                author_id=users["john@smart.support"].id, tags=tags,
                view_count=145, helpful_count=120, not_helpful_count=10,
                usage_count=89, current_version=1, published_at=_now(days=4),
            )
            db.add(art)
            db.flush()
            db.add(KBArticleVersion(
                article_id=art.id, version=1, title=title, content=content,
                summary=summary, changed_by=users["john@smart.support"].id,
                change_summary="Initial version", created_at=_now(days=4),
            ))

    # -- Notifications -------------------------------------------------------
    if db.scalar(select(Notification).limit(1)) is None:
        admin_id = str(users["admin@smart.support"].id)
        db.add_all([
            Notification(user_id=admin_id, type="ticket.assigned",
                         title="Ticket assigned", message="TKT-000002 was assigned to Emma Wilson"),
            Notification(user_id=admin_id, type="sla.warning",
                         title="SLA approaching breach", message="An urgent ticket is nearing its first-response SLA"),
            Notification(user_id=str(users["emma@smart.support"].id), type="ai.review",
                         title="AI classification needs review", message="A new ticket had a low-confidence classification"),
        ])

    db.commit()
    print("Seed complete.")
    print(f"  Users: {[u.email for u in db.scalars(select(User)).all()]}")
    print(f"  Tickets: {len(db.scalars(select(Ticket)).all())}")
    print(f"  KB articles: {len(db.scalars(select(KBArticle)).all())}")


def main() -> None:
    Base.metadata.create_all(bind=engine)  # ensure tables exist
    with SessionLocal() as db:
        seed(db)


if __name__ == "__main__":
    main()
