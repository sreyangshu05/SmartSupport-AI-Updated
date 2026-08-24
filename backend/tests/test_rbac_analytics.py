"""Role-based access control boundaries and DB-backed analytics."""


# ---- RBAC ----

def test_admin_can_manage_agents(client, admin_auth, seed_user_ctx):
    r = client.patch(
        f"/api/agents/{seed_user_ctx['admin_id']}",
        headers=admin_auth,
        json={"role": "senior_agent"},
    )
    # The seed just created a real admin; this path is admin-gated even if id is bogus.
    assert r.status_code == 200


def test_agent_cannot_manage_agents(client, agent_auth):
    r = client.patch("/api/agents/whatever", headers=agent_auth, json={"role": "admin"})
    assert r.status_code == 403


def test_agent_cannot_read_audit_logs(client, agent_auth):
    r = client.get("/api/audit-logs", headers=agent_auth)
    assert r.status_code == 403


def test_admin_can_read_audit_logs(client, admin_auth):
    r = client.get("/api/audit-logs?page_size=5", headers=admin_auth)
    assert r.status_code == 200


def test_agent_can_read_tickets(client, agent_auth):
    r = client.get("/api/tickets", headers=agent_auth)
    assert r.status_code == 200


# ---- Analytics computed from real DB data ----

def test_analytics_overview_from_db(client, admin_auth):
    # create a few tickets
    for s in ["a", "b", "c"]:
        client.post("/api/tickets", headers=admin_auth,
                    json={"subject": f"issue {s}", "description": "long enough description body goes here.",
                          "priority": "low", "customer_email": f"{s}@ex.com"})
    r = client.get("/api/analytics/overview", headers=admin_auth)
    assert r.status_code == 200
    body = r.json()
    assert body["total_tickets"] >= 3
    assert body["tickets_by_status"]["open"] >= 3
    assert body["tickets_by_priority"]["low"] >= 3


def test_analytics_requires_auth(client):
    assert client.get("/api/analytics/overview").status_code == 401


# ---- Audit trail is append-only ----

def test_audit_log_records_actions(client, admin_auth):
    t = client.post("/api/tickets", headers=admin_auth,
                    json={"subject": "audit trail", "description": "body of enough length here please.",
                          "priority": "medium", "customer_email": "x@ex.com"}).json()
    client.patch(f"/api/tickets/{t['id']}", headers=admin_auth, json={"status": "in_progress"})
    r = client.get("/api/audit-logs?page_size=20", headers=admin_auth)
    actions = [a for a in r.json()["items"] if a["resource_type"] == "ticket" and a["resource_id"] == t["id"]]
    assert len(actions) >= 1
    assert actions[0]["action"] in ("ticket.update", "ticket.status_update", "ticket.updated", "ticket.create")


# ---- Reliability: graceful 404s ----

def test_missing_ticket_returns_404(client, admin_auth):
    r = client.get("/api/tickets/00000000-0000-0000-0000-000000000000", headers=admin_auth)
    assert r.status_code == 404


def test_unknown_route_returns_404(client, admin_auth):
    r = client.get("/api/does-not-exist", headers=admin_auth)
    assert r.status_code == 404


# ---- Agent subclass (agents table) population ----

def test_create_agent_persists_agent_subclass_row(client, admin_auth, db_session):
    """Creating an agent must populate both the users and agents tables with
    real support-specific fields (joined-table inheritance), not just a User row.
    """
    from sqlalchemy import select
    from app.models.user import Agent, User

    r = client.post(
        "/api/agents",
        headers=admin_auth,
        json={
            "email": "new.agent@test.com",
            "full_name": "Newly Hired",
            "role": "agent",
            "title": "L2 Support",
            "skills": ["networking", "ssh"],
            "max_concurrent_tickets": 4,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["title"] == "L2 Support"
    assert body["skills"] == ["networking", "ssh"]
    assert body["availability"] == "online"

    # The API response id is the shared users.id; the agents row must exist keyed on it.
    uid = body["id"]
    user = db_session.get(User, uid)
    assert user is not None, "users row missing"
    agent = db_session.get(Agent, uid)
    assert agent is not None, "agents subclass row missing"
    assert agent.title == "L2 Support"
    assert agent.skills == ["networking", "ssh"]
    assert agent.max_concurrent_tickets == 4

    # Listing must surface the real agent fields too.
    lst = client.get("/api/agents", headers=admin_auth).json()
    created = next((a for a in lst if a["email"] == "new.agent@test.com"), None)
    assert created is not None
    assert created["title"] == "L2 Support"
    assert created["skills"] == ["networking", "ssh"]


def test_update_agent_writes_support_fields(client, admin_auth, db_session):
    from app.models.user import Agent, User

    created = client.post(
        "/api/agents", headers=admin_auth,
        json={"email": "updatable.agent@test.com", "full_name": "Update Me",
              "role": "agent", "title": "T1", "skills": ["a"], "availability": "away"},
    ).json()
    r = client.patch(
        f"/api/agents/{created['id']}", headers=admin_auth,
        json={"skills": ["a", "b", "c"], "availability": "offline", "max_concurrent_tickets": 2},
    )
    assert r.status_code == 200, r.text
    agent = db_session.get(Agent, created["id"])
    assert agent.skills == ["a", "b", "c"]
    assert agent.availability == "offline"
    assert agent.max_concurrent_tickets == 2
    assert r.json()["skills"] == ["a", "b", "c"]


def test_plain_user_serializes_without_agent_row(client, seed_user_ctx, admin_auth):
    """Users created before/as plain users (no agents row) still serialize cleanly."""
    lst = client.get("/api/agents", headers=admin_auth)
    assert lst.status_code == 200
    for a in lst.json():
        assert "title" in a and "skills" in a and "availability" in a
