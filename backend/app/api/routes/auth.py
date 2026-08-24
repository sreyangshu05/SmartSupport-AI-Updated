"""Authentication routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser, get_current_user
from app.core.database import get_db
from app.schemas.auth import (
    CurrentUserOut,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(
    body: RegisterRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    svc = AuthService(db)
    user = svc.register(email=body.email, password=body.password, full_name=body.full_name)
    AuditService(db).record(
        actor_id=str(user.id),
        actor_email=user.email,
        action="user.register",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
    )
    AuditService(db).commit()
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    svc = AuthService(db)
    user = svc.authenticate(email=body.email, password=body.password)
    token = svc.login(email=body.email, password=body.password)
    AuditService(db).record(
        actor_id=str(user.id),
        actor_email=user.email,
        action="auth.login",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
    )
    AuditService(db).commit()
    return token


@router.get("/me", response_model=CurrentUserOut)
def me(current: Annotated[CurrentUser, Depends(get_current_user)]):
    return {
        "id": current.id,
        "email": current.user.email,
        "full_name": current.user.full_name,
        "role": current.role,
        "is_active": current.user.is_active,
        "permissions": sorted(current.permissions),
    }
