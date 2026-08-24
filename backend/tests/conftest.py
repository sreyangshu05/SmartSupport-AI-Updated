"""Pytest fixtures: an isolated test database and an ASGI test client."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Use the test database for the suite.
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://smartuser:smartpass@127.0.0.1:5432/smartsupport_test",
)


@pytest.fixture(scope="function")
def test_engine():
    """A fresh schema per test for isolation."""
    engine = create_engine(TEST_DB_URL)
    from app.models import Base

    # Deterministic reset: cycle the whole schema instead of relying on
    # drop_all, which can miss orphan indexes/constraints left by migrations.
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(bind=engine)
    yield engine
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))


@pytest.fixture()
def db_session(test_engine):
    Session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(test_engine, monkeypatch):
    """App with its DB dependency overridden to the isolated test database."""
    from app.core import database
    from app.main import app
    from app.auth.deps import get_current_user

    Session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[database.get_db] = override_get_db
    # Re-bind the app's own SessionLocal so service modules using it resolve too.
    database.engine = test_engine
    database.SessionLocal.configure(bind=test_engine)

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def seed_user_ctx(client, db_session):
    """Create an admin, senior, and agent user; return bearer tokens."""
    from app.services.auth_service import AuthService

    svc = AuthService(db_session)
    admin = svc.register(email="admin@test.com", password="password1", full_name="Admin User")
    from app.models.enums import RoleEnum
    admin.role = RoleEnum.ADMIN
    db_session.commit()

    senior = svc.register(email="senior@test.com", password="password1", full_name="Senior User")
    senior.role = RoleEnum.SENIOR_AGENT
    db_session.commit()

    agent = svc.register(email="agent@test.com", password="password1", full_name="Agent User")
    agent.role = RoleEnum.AGENT
    db_session.commit()

    def token_for(email: str, password: str = "password1"):
        r = client.post("/api/auth/login", json={"email": email, "password": password})
        assert r.status_code == 200, r.text
        return r.json()["access_token"]

    return {
        "admin_token": token_for("admin@test.com"),
        "senior_token": token_for("senior@test.com"),
        "agent_token": token_for("agent@test.com"),
        "admin_id": str(admin.id),
        "senior_id": str(senior.id),
        "agent_id": str(agent.id),
    }


@pytest.fixture()
def admin_auth(seed_user_ctx):
    return {"Authorization": f"Bearer {seed_user_ctx['admin_token']}"}


@pytest.fixture()
def agent_auth(seed_user_ctx):
    return {"Authorization": f"Bearer {seed_user_ctx['agent_token']}"}
