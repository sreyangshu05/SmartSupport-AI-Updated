"""In-app notification routes."""
from __future__ import annotations

from typing import Annotated

import json
import asyncio
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser, get_current_user
from app.auth.security import decode_access_token
from app.core.database import get_db
from app.models.user import User
from app.schemas.admin import NotificationOut
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


async def _notification_stream(request: Request, svc: NotificationService, user_id: str):
    seen: set[str] = set()
    while True:
        if await request.is_disconnected():
            break
        items = svc.list_for_user(user_id)
        payload = [n for n in items if n.id not in seen]
        for n in payload:
            seen.add(n.id)
            yield f"data: {json.dumps({'id': n.id, 'type': n.type, 'title': n.title, 'message': n.message, 'link': n.link, 'read_at': n.read_at.isoformat() if n.read_at else None, 'created_at': n.created_at.isoformat()})}\n\n"
        await asyncio.sleep(10)


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    current: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    unread_only: bool = False,
):
    svc = NotificationService(db)
    return svc.list_for_user(current.id, unread_only=unread_only)


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: str,
    current: Annotated[CurrentUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    svc = NotificationService(db)
    n = svc.mark_read(notification_id, current.id)
    if n is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Notification not found")
    return n


@router.get("/stream")
async def stream_notifications(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    token: str | None = None,
):
    if not token:
        from fastapi import HTTPException
        raise HTTPException(401, "Not authenticated")
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        from fastapi import HTTPException
        raise HTTPException(401, "Not authenticated")
    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        from fastapi import HTTPException
        raise HTTPException(401, "Not authenticated")
    svc = NotificationService(db)
    return StreamingResponse(
        _notification_stream(request, svc, str(user.id)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
