"""Authentication service: login, register, session validation."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import permissions_for_role
from app.auth.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.enums import RoleEnum, sval
from app.models.user import User

_InvalidCredentials = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid email or password",
    headers={"WWW-Authenticate": "Bearer"},
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def register(self, *, email: str, password: str, full_name: str) -> User:
        existing = self.db.scalar(select(User).where(User.email == email))
        if existing:
            raise HTTPException(
                status_code=409, detail="An account with that email already exists"
            )
        user = User(
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=RoleEnum.AGENT,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate(self, *, email: str, password: str) -> User:
        user = self.db.scalar(select(User).where(User.email == email))
        if user is None or not user.password_hash:
            raise _InvalidCredentials
        if not verify_password(password, user.password_hash):
            raise _InvalidCredentials
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated")
        return user

    def login(self, *, email: str, password: str) -> dict:
        user = self.authenticate(email=email, password=password)
        user.touch_last_active()
        self.db.commit()
        token = create_access_token(str(user.id), sval(user.role))
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 60 * 8,
        }

    def build_context(self, user: User) -> dict:
        perms = sorted(permissions_for_role(user.role))
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": sval(user.role),
            "is_active": user.is_active,
            "permissions": perms,
        }
