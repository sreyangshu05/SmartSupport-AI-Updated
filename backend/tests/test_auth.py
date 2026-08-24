"""Authentication: login, register, session, protected routes."""


def test_register(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "new@test.com", "password": "password1", "full_name": "New User"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == "new@test.com"
    assert body["role"] == "agent"


def test_login_success(client, seed_user_ctx):
    r = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "password1"})
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.json()["token_type"] == "bearer"


def test_login_wrong_password(client, seed_user_ctx):
    r = client.post("/api/auth/login", json={"email": "admin@test.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post("/api/auth/login", json={"email": "nobody@test.com", "password": "password1"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_role_and_permissions(client, seed_user_ctx):
    r = client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {seed_user_ctx['admin_token']}"
    })
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "admin"
    assert "tickets.read" in body["permissions"]
    assert "admin.manage" in body["permissions"]


def test_invalid_token_rejected(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.valid.token"})
    assert r.status_code == 401
