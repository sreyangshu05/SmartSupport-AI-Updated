"""Knowledge Base routes with draft lifecycle + permissions."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.ai.service import TicketAIService
from app.auth.deps import CurrentUser, require_permission
from app.auth.permissions import (
    KB_CREATE,
    KB_DELETE,
    KB_PUBLISH,
    KB_READ,
    KB_UPDATE,
)
from app.core.database import get_db
from app.models.enums import KBArticleStatus
from app.models.kb import KBArticle as KBArticleModel
from app.models.user import User
from app.schemas.kb import (
    ArticleStats,
    KBArticleCreate,
    KBArticleOut,
    KBArticleUpdate,
    KBArticleVersionOut,
    KBFeedbackCreate,
    PagedKB,
    VersionRollbackRequest,
)
from app.services.audit_service import AuditService
from app.services.kb_service import KBService

router = APIRouter(prefix="/kb/articles", tags=["knowledge-base"])


def _serialize(art: KBArticleModel, db: Session, category_name: str | None = None) -> dict:
    author = db.get(User, art.author_id) if art.author_id else None
    return {
        "id": str(art.id),
        "title": art.title,
        "content": art.content,
        "summary": art.summary,
        "status": art.status.value if hasattr(art.status, "value") else art.status,
        "tags": art.tags or [],
        "view_count": art.view_count,
        "helpful_count": art.helpful_count,
        "not_helpful_count": art.not_helpful_count,
        "usage_count": art.usage_count,
        "category_id": str(art.category_id) if art.category_id else None,
        "category": category_name,
        "author_name": author.full_name if author else None,
        "created_at": art.created_at,
        "updated_at": art.updated_at,
        "published_at": art.published_at,
        "current_version": art.current_version,
    }


def _category_name(db: Session, category_id: str | None) -> str | None:
    if not category_id:
        return None
    from app.models.ticket import TicketCategory
    c = db.get(TicketCategory, category_id)
    return c.name if c else None


@router.get("", response_model=PagedKB)
def list_articles(
    current: Annotated[CurrentUser, Depends(require_permission(KB_READ))],
    db: Annotated[Session, Depends(get_db)],
    search: str | None = None,
    category_id: str | None = None,
    status: KBArticleStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    svc = KBService(db)
    result = svc.list_articles(current, search=search, category_id=category_id, status=status, page=page, page_size=page_size)
    return {
        "items": [_serialize(a, db, _category_name(db, a.category_id)) for a in result["items"]],
        "total": result["total"], "page": result["page"], "page_size": result["page_size"], "pages": result["pages"],
    }


@router.post("", response_model=KBArticleOut, status_code=201)
def create_article(
    body: KBArticleCreate,
    current: Annotated[CurrentUser, Depends(require_permission(KB_CREATE))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    svc = KBService(db)
    art = svc.create_article(current, title=body.title, content=body.content, summary=body.summary, category_id=body.category_id, tags=body.tags)
    AuditService(db).record(actor_id=current.id, actor_email=current.user.email, action="kb.create", resource_type="kb_article",
                            resource_id=str(art.id), request=request)
    AuditService(db).commit()
    # Best-effort: index the article for RAG retrieval (no-op without AI/pgvector).
    TicketAIService().embed_article(art)
    return _serialize(art, db, _category_name(db, art.category_id))


@router.post("/{article_id}/publish", response_model=KBArticleOut)
def publish_article(
    article_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(KB_PUBLISH))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    svc = KBService(db)
    art = svc.set_status(article_id, current, KBArticleStatus.PUBLISHED)
    AuditService(db).record(actor_id=current.id, actor_email=current.user.email, action="kb.publish", resource_type="kb_article",
                            resource_id=str(art.id), request=request)
    AuditService(db).commit()
    return _serialize(art, db, _category_name(db, art.category_id))


@router.post("/{article_id}/status", response_model=KBArticleOut)
def set_status(
    article_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(KB_UPDATE))],
    db: Annotated[Session, Depends(get_db)],
    status: KBArticleStatus = Query(...),
):
    svc = KBService(db)
    art = svc.set_status(article_id, current, status)
    return _serialize(art, db, _category_name(db, art.category_id))


@router.get("/{article_id}", response_model=KBArticleOut)
def get_article(
    article_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(KB_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    svc = KBService(db)
    art = svc.get_article(article_id, current)
    return _serialize(art, db, _category_name(db, art.category_id))


@router.patch("/{article_id}", response_model=KBArticleOut)
def update_article(
    article_id: str,
    body: KBArticleUpdate,
    current: Annotated[CurrentUser, Depends(require_permission(KB_UPDATE))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    svc = KBService(db)
    updates = body.model_dump(exclude_unset=True)
    art = svc.update_article(article_id, current, title=updates.get("title"), content=updates.get("content"),
                             summary=updates.get("summary"), category_id=updates.get("category_id"),
                             tags=updates.get("tags"), change_summary=updates.get("change_summary"))
    AuditService(db).record(actor_id=current.id, actor_email=current.user.email, action="kb.update", resource_type="kb_article",
                            resource_id=str(art.id), request=request)
    AuditService(db).commit()
    # Re-index when content may have changed (best-effort).
    if updates.get("title") is not None or updates.get("content") is not None:
        TicketAIService().embed_article(art)
    return _serialize(art, db, _category_name(db, art.category_id))


@router.delete("/{article_id}", status_code=204)
def delete_article(
    article_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(KB_DELETE))],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    svc = KBService(db)
    svc.delete_article(article_id, current)
    AuditService(db).record(actor_id=current.id, actor_email=current.user.email, action="kb.delete", resource_type="kb_article",
                            resource_id=article_id, request=request)
    AuditService(db).commit()


@router.get("/{article_id}/versions", response_model=list[KBArticleVersionOut])
def versions(
    article_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(KB_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    svc = KBService(db)
    return svc.versions(article_id, current)


@router.post("/{article_id}/rollback", response_model=KBArticleOut)
def rollback(
    article_id: str,
    body: VersionRollbackRequest,
    current: Annotated[CurrentUser, Depends(require_permission(KB_UPDATE))],
    db: Annotated[Session, Depends(get_db)],
):
    svc = KBService(db)
    art = svc.rollback(article_id, current, body.version)
    return _serialize(art, db, _category_name(db, art.category_id))


@router.post("/{article_id}/view", response_model=KBArticleOut)
def record_view(
    article_id: str,
    current: Annotated[CurrentUser, Depends(require_permission(KB_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    svc = KBService(db)
    svc.record_view(article_id, current)
    art = svc.get_article(article_id, current)
    return _serialize(art, db, _category_name(db, art.category_id))


@router.post("/{article_id}/feedback")
def feedback(
    article_id: str,
    body: KBFeedbackCreate,
    current: Annotated[CurrentUser, Depends(require_permission(KB_READ))],
    db: Annotated[Session, Depends(get_db)],
):
    svc = KBService(db)
    svc.record_feedback(article_id, current, body.helpful)
    art = svc.get_article(article_id, current)
    total = (art.helpful_count + art.not_helpful_count) or 1
    return {
        "views": art.view_count, "helpful": art.helpful_count, "not_helpful": art.not_helpful_count,
        "usage": art.usage_count, "helpful_rate": round(art.helpful_count / total, 3),
    }
