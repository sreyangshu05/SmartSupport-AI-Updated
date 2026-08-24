"""Knowledge Base content service with draft lifecycle + versioning."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import Text, func, or_, select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.models.enums import KBArticleStatus, sval
from app.models.kb import (
    KBArticle,
    KBArticleVersion,
    KBArticleView,
    KBFeedback,
)
from app.models.user import User

# Lifecycle transitions.
KB_TRANSITIONS: dict[KBArticleStatus, set[KBArticleStatus]] = {
    KBArticleStatus.DRAFT: {KBArticleStatus.REVIEW, KBArticleStatus.ARCHIVED},
    KBArticleStatus.REVIEW: {
        KBArticleStatus.DRAFT,
        KBArticleStatus.APPROVED,
        KBArticleStatus.ARCHIVED,
    },
    KBArticleStatus.APPROVED: {
        KBArticleStatus.PUBLISHED,
        KBArticleStatus.DRAFT,
        KBArticleStatus.ARCHIVED,
    },
    KBArticleStatus.PUBLISHED: {KBArticleStatus.ARCHIVED, KBArticleStatus.DRAFT},
    KBArticleStatus.ARCHIVED: {KBArticleStatus.DRAFT},
}


class KBArticleNotFound(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=404, detail="Knowledge base article not found")


class InvalidKBTransition(HTTPException):
    def __init__(self, current: KBArticleStatus, requested: KBArticleStatus) -> None:
        super().__init__(
            status_code=400,
            detail=f"Cannot move article from {sval(current)} to {sval(requested)}",
        )


class KBService:
    def __init__(self, db: Session):
        self.db = db

    def _snapshot(self, article: KBArticle, changed_by: str | None, change_summary: str | None) -> KBArticleVersion:
        version = KBArticleVersion(
            article_id=article.id,
            version=article.current_version,
            title=article.title,
            content=article.content,
            summary=article.summary,
            changed_by=changed_by,
            change_summary=change_summary,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(version)
        return version

    def get_article(self, article_id: str, actor: CurrentUser) -> KBArticle:
        art = self.db.get(KBArticle, article_id)
        if art is None:
            raise KBArticleNotFound()
        return art

    def list_articles(
        self,
        actor: CurrentUser,
        *,
        search: str | None = None,
        category_id: str | None = None,
        status: KBArticleStatus | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        stmt = select(KBArticle)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                or_(
                    KBArticle.title.ilike(like),
                    KBArticle.content.ilike(like),
                    KBArticle.tags.cast(Text).ilike(like),
                )
            )
        if category_id:
            stmt = stmt.where(KBArticle.category_id == category_id)
        if status:
            stmt = stmt.where(KBArticle.status == status)
        else:
            # Default: surfaced articles, exclude archived unless requested.
            stmt = stmt.where(KBArticle.status != KBArticleStatus.ARCHIVED)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        stmt = stmt.order_by(KBArticle.updated_at.desc()) \
            .offset((page - 1) * page_size).limit(page_size)
        items = self.db.scalars(stmt).all()
        pages = max(1, (total + page_size - 1) // page_size)
        return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages}

    def create_article(
        self,
        actor: CurrentUser,
        *,
        title: str,
        content: str,
        summary: str | None,
        category_id: str | None,
        tags: list[str],
    ) -> KBArticle:
        article = KBArticle(
            title=title,
            content=content,
            summary=summary,
            category_id=category_id,
            tags=[t.strip().lower() for t in tags if t.strip()],
            status=KBArticleStatus.DRAFT,
            author_id=actor.id,
            current_version=0,  # first snapshot will bump to 1
        )
        self.db.add(article)
        self.db.flush()
        self._snapshot(article, actor.id, "Initial version")
        article.current_version = 1
        article.status = KBArticleStatus.DRAFT
        self.db.commit()
        self.db.refresh(article)
        return article

    def update_article(
        self,
        article_id: str,
        actor: CurrentUser,
        *,
        title: str | None,
        content: str | None,
        summary: str | None,
        category_id: str | None,
        tags: list[str] | None,
        change_summary: str | None,
    ) -> KBArticle:
        article = self.get_article(article_id, actor)

        if title is not None:
            article.title = title
        if content is not None:
            article.content = content
        if summary is not None:
            article.summary = summary
        if category_id is not None:
            article.category_id = category_id
        if tags is not None:
            article.tags = [t.strip().lower() for t in tags if t.strip()]

        self._snapshot(article, actor.id, change_summary or "Update")
        article.current_version += 1
        self.db.commit()
        self.db.refresh(article)
        return article

    def set_status(self, article_id: str, actor: CurrentUser, target: KBArticleStatus) -> KBArticle:
        article = self.get_article(article_id, actor)
        allowed = KB_TRANSITIONS.get(article.status, set())
        if target == article.status:
            return article
        if target not in allowed:
            raise InvalidKBTransition(article.status, target)

        if target == KBArticleStatus.PUBLISHED:
            article.published_at = datetime.now(timezone.utc)
        article.status = target
        self._snapshot(article, actor.id, f"Status → {target.value}")
        article.current_version += 1
        self.db.commit()
        self.db.refresh(article)
        return article

    def delete_article(self, article_id: str, actor: CurrentUser) -> None:
        article = self.get_article(article_id, actor)
        # Soft-archive is safer than hard delete for an audit-friendly KB.
        article.status = KBArticleStatus.ARCHIVED
        article.tags = article.tags or []
        self.db.commit()

    def versions(self, article_id: str, actor: CurrentUser) -> list[KBArticleVersion]:
        self.get_article(article_id, actor)
        return list(
            self.db.scalars(
                select(KBArticleVersion)
                .where(KBArticleVersion.article_id == article_id)
                .order_by(KBArticleVersion.version.desc())
            )
        )

    def rollback(self, article_id: str, actor: CurrentUser, version: int) -> KBArticle:
        article = self.get_article(article_id, actor)
        target = self.db.scalar(
            select(KBArticleVersion).where(
                KBArticleVersion.article_id == article_id,
                KBArticleVersion.version == version,
            )
        )
        if target is None:
            raise HTTPException(status_code=404, detail="Requested version not found")
        article.title = target.title
        article.content = target.content
        article.summary = target.summary
        self._snapshot(article, actor.id, f"Rollback to v{version}")
        article.current_version += 1
        self.db.commit()
        self.db.refresh(article)
        return article

    def record_view(self, article_id: str, actor: CurrentUser) -> None:
        article = self.get_article(article_id, actor)
        article.view_count += 1
        self.db.add(KBArticleView(article_id=article.id, viewer_id=actor.id))
        self.db.commit()

    def record_feedback(self, article_id: str, actor: CurrentUser, helpful: bool) -> None:
        article = self.get_article(article_id, actor)
        if helpful:
            article.helpful_count += 1
        else:
            article.not_helpful_count += 1
        self.db.add(
            KBFeedback(article_id=article.id, user_id=actor.id, helpful=helpful)
        )
        self.db.commit()

    def increment_usage(self, article_id: str) -> None:
        art = self.db.get(KBArticle, article_id)
        if art is not None:
            art.usage_count += 1
            self.db.commit()
