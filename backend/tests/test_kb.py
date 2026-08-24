"""Knowledge Base: draft lifecycle, publishing, versions, feedback."""


def _mk_article(client, auth, overrides=None):
    payload = {
        "title": "How to Reset Password",
        "content": "Click forgot password, enter email, follow the reset link.",
        "summary": "Password reset guide",
        "tags": ["password"],
    }
    if overrides:
        payload.update(overrides)
    return client.post("/api/kb/articles", headers=auth, json=payload)


def test_create_article_starts_draft(client, admin_auth):
    r = _mk_article(client, admin_auth)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "draft"
    assert r.json()["current_version"] == 1


def test_article_persists(client, admin_auth):
    art = _mk_article(client, admin_auth)
    _ = art
    a = _mk_article(client, admin_auth, overrides={"title": "Billing FAQ", "content": "How billing works."})
    r = client.get(f"/api/kb/articles/{a.json()['id']}", headers=admin_auth)
    assert r.status_code == 200
    assert r.json()["title"] == "Billing FAQ"


def test_publish_workflow(client, admin_auth):
    a = _mk_article(client, admin_auth)
    aid = a.json()["id"]
    r = client.post(f"/api/kb/articles/{aid}/status", headers=admin_auth, params={"status": "approve_intent"})
    # invalid enum should 422
    assert r.status_code == 422
    # move draft -> review -> approved -> published
    assert client.post(f"/api/kb/articles/{aid}/status", headers=admin_auth, params={"status": "review"}).status_code == 200
    assert client.post(f"/api/kb/articles/{aid}/status", headers=admin_auth, params={"status": "approved"}).status_code == 200
    r = client.post(f"/api/kb/articles/{aid}/publish", headers=admin_auth)
    assert r.status_code == 200
    assert r.json()["status"] == "published"
    assert r.json()["published_at"] is not None


def test_invalid_kb_transition(client, admin_auth):
    a = _mk_article(client, admin_auth)  # draft
    aid = a.json()["id"]
    # draft -> approved is invalid (must go through review)
    r = client.post(f"/api/kb/articles/{aid}/status", headers=admin_auth, params={"status": "approved"})
    assert r.status_code == 400


def test_update_creates_version(client, admin_auth):
    a = _mk_article(client, admin_auth)
    aid = a.json()["id"]
    r = client.patch(f"/api/kb/articles/{aid}", headers=admin_auth,
                     json={"content": "Updated content with more detail."})
    assert r.status_code == 200
    assert r.json()["current_version"] == 2


def test_versions_listed(client, admin_auth):
    a = _mk_article(client, admin_auth)
    aid = a.json()["id"]
    client.patch(f"/api/kb/articles/{aid}", headers=admin_auth, json={"content": "version two content."})
    r = client.get(f"/api/kb/articles/{aid}/versions", headers=admin_auth)
    assert r.status_code == 200
    versions = r.json()
    assert len(versions) >= 2
    assert versions[0]["version"] > versions[1]["version"]  # newest first


def test_feedback_updates_metrics(client, admin_auth):
    a = _mk_article(client, admin_auth)
    aid = a.json()["id"]
    r = client.post(f"/api/kb/articles/{aid}/feedback", headers=admin_auth, json={"helpful": True})
    assert r.status_code == 200
    assert r.json()["helpful"] == 1


def test_kb_search(client, admin_auth):
    _mk_article(client, admin_auth, overrides={"title": "Dark Mode Guide", "content": "Enable dark mode."})
    _mk_article(client, admin_auth, overrides={"title": "Refund Policy", "content": "Refunds within 30 days."})
    r = client.get("/api/kb/articles?search=dark", headers=admin_auth)
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["title"] == "Dark Mode Guide"
