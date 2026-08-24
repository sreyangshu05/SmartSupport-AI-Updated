"""FastAPI dependencies for authenticated users and permission checks."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.permissions import role_has_permission
from app.auth.security import decode_access_token
from app.core.database import get_db
from app.models.enums import RoleEnum, sval
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

_CredentialsError = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


class CurrentUser:
    """Bundle of the authenticated user + their permission set."""

    def __init__(self, user: User, permissions: set[str]):
        self.user = user
        self.permissions = permissions

    @property
    def id(self) -> str:
        return self.user.id

    @property
    def role(self) -> RoleEnum:
        return self.user.role

    def has(self, permission: str) -> bool:
        return permission in self.permissions

    def require(self, permission: str) -> None:
        if permission not in self.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUser:
    if credentials is None:
        raise _CredentialsError
    payload = decode_access_token(credentials.credentials)
    if payload is None or "sub" not in payload:
        raise _CredentialsError

    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise _CredentialsError

    role = payload.get("role")
    if role is not None and role != sval(user.role):
        # Token role and DB role diverged (role changed after login); trust DB.
        pass

    from app.auth.permissions import permissions_for_role

    return CurrentUser(user, permissions_for_role(user.role))


def require_permission(permission: str):
    def dependency(current: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        current.require(permission)
        return current

    return dependency
