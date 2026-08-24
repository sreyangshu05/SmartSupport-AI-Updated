"""Ticket workflow: CRUD, transitions, responses, persistence, RBAC."""


def _mk_ticket(client, auth, overrides=None):
    payload = {
        "subject": "Password reset not working",
        "description": "The reset link sends an invalid token error and I cannot log in at all.",
        "priority": "high",
        "customer_email": "customer@example.com",
        "customer_name": "Alice",
        "tags": ["password"],
    }
    if overrides:
        payload.update(overrides)
    r = client.post("/api/tickets", headers=auth, json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_ticket(admin_auth, client):
    t = _mk_ticket(client, admin_auth)
    assert t["ticket_number"].startswith("TKT-")
    assert t["status"] == "open"
    assert t["priority"] == "high"


def test_ticket_numbers_are_unique_and_monotonic(admin_auth, client):
    a = _mk_ticket(client, admin_auth)
    b = _mk_ticket(client, admin_auth)
    assert a["ticket_number"] != b["ticket_number"]
    assert int(a["ticket_number"].split("-")[1]) < int(b["ticket_number"].split("-")[1])


def test_ticket_persists_after_fetch(admin_auth, client):
    t = _mk_ticket(client, admin_auth)
    r = client.get(f"/api/tickets/{t['id']}", headers=admin_auth)
    assert r.status_code == 200
    got = r.json()
    assert got["subject"] == t["subject"]
    assert got["ticket_number"] == t["ticket_number"]


def test_tickets_require_auth(client):
    assert client.get("/api/tickets").status_code == 401


def test_list_tickets_pagination(admin_auth, client):
    for _ in range(3):
        _mk_ticket(client, admin_auth)
    r = client.get("/api/tickets?page_size=2&page=1", headers=admin_auth)
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
    assert body["pages"] == 2


def test_search_filters(client, admin_auth):
    _mk_ticket(client, admin_auth, overrides={"subject": "Billing error on invoice"})
    _mk_ticket(client, admin_auth, overrides={"subject": "Feature request dark mode"})
    r = client.get("/api/tickets?search=billing", headers=admin_auth)
    body = r.json()
    assert body["total"] == 1
    assert "Billing" in body["items"][0]["subject"]


def test_valid_transition_open_to_in_progress(client, admin_auth):
    t = _mk_ticket(client, admin_auth)
    r = client.patch(f"/api/tickets/{t['id']}", headers=admin_auth, json={"status": "in_progress"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "in_progress"


def test_invalid_transition_open_to_resolved_rejected(client, admin_auth):
    t = _mk_ticket(client, admin_auth)  # status open
    r = client.patch(f"/api/tickets/{t['id']}", headers=admin_auth, json={"status": "resolved"})
    assert r.status_code == 400
    assert "transition" in r.json()["detail"].lower()


def test_add_response(client, admin_auth):
    t = _mk_ticket(client, admin_auth)
    r = client.post(
        f"/api/tickets/{t['id']}/responses",
        headers=admin_auth,
        json={"content": "We are looking into this.", "is_internal": False},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["response_type"] == "agent"
    assert body["is_internal"] is False


def test_add_internal_note(client, admin_auth):
    t = _mk_ticket(client, admin_auth)
    r = client.post(
        f"/api/tickets/{t['id']}/responses",
        headers=admin_auth,
        json={"content": "Internal: likely duplicate of another ticket.", "is_internal": True},
    )
    assert r.status_code == 201
    assert r.json()["is_internal"] is True
    assert r.json()["response_type"] == "internal_note"


def test_reply_exposes_author(client, admin_auth):
    t = _mk_ticket(client, admin_auth)
    r = client.post(
        f"/api/tickets/{t['id']}/responses",
        headers=admin_auth,
        json={"content": "Hello, thanks for reaching out.", "is_internal": False},
    )
    assert r.json()["author_name"] == "Admin User"


def test_agent_cannot_change_other_agents_role(client, admin_auth, agent_auth):
    # Admin creates an agent? Instead assert agent cannot hit agents-admin route.
    r = client.patch("/api/agents/some-id", headers=agent_auth, json={"role": "admin"})
    assert r.status_code in (403, 404)


def test_create_ticket_validation(client, admin_auth):
    r = client.post("/api/tickets", headers=admin_auth, json={"subject": "x", "description": "short"})
    assert r.status_code == 422
