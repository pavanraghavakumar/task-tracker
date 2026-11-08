import sqlite3

import pytest

from backend.app import create_app


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db"), "SECRET_KEY": "test-secret"})
    return app.test_client()


def register(client, email="alex@example.com"):
    response = client.post("/api/v1/auth/register", json={"name": "Alex User", "email": email, "password": "Secure123"})
    assert response.status_code == 201
    return response.get_json()["data"]["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_registration_hashes_password_and_authenticates(client):
    token = register(client)
    login = client.post("/api/v1/auth/login", json={"email": "alex@example.com", "password": "Secure123"})
    assert login.status_code == 200
    assert login.get_json()["success"] is True
    me = client.get("/api/v1/auth/me", headers=auth(token))
    assert me.get_json()["data"]["email"] == "alex@example.com"

    with sqlite3.connect(client.application.config["DATABASE"]) as db:
        password_hash = db.execute("SELECT password_hash FROM users").fetchone()[0]
    assert password_hash != "Secure123"
    assert password_hash.startswith("scrypt:")


def test_registration_validation_and_duplicate_email(client):
    invalid = client.post("/api/v1/auth/register", json={"name": "A", "email": "bad", "password": "short"})
    assert invalid.status_code == 400
    assert set(invalid.get_json()["error"]["details"]) == {"name", "email", "password"}
    register(client)
    duplicate = client.post("/api/v1/auth/register", json={"name": "Alex User", "email": "ALEX@example.com", "password": "Secure123"})
    assert duplicate.status_code == 409


def test_full_category_and_task_lifecycle(client):
    token = register(client)
    headers = auth(token)
    category = client.post("/api/v1/categories", headers=headers, json={"name": "Work", "color": "#2563EB"})
    assert category.status_code == 201
    category_id = category.get_json()["data"]["id"]

    created = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"title": "Write report", "description": "Quarterly report", "priority": "high", "status": "pending", "due_date": "2099-01-02", "category_id": category_id},
    )
    assert created.status_code == 201
    task_id = created.get_json()["data"]["id"]

    listed = client.get("/api/v1/tasks?search=report&priority=high&status=pending&sort_by=due_date&sort_order=asc", headers=headers)
    assert listed.get_json()["data"]["pagination"]["total"] == 1
    assert listed.get_json()["data"]["items"][0]["category"]["name"] == "Work"

    updated = client.patch(f"/api/v1/tasks/{task_id}", headers=headers, json={"status": "completed", "priority": "low"})
    assert updated.status_code == 200
    assert updated.get_json()["data"]["completed_at"] is not None

    activity = client.get(f"/api/v1/tasks/{task_id}/activity", headers=headers).get_json()["data"]
    assert [item["action"] for item in activity] == ["updated", "created"]
    assert client.delete(f"/api/v1/tasks/{task_id}", headers=headers).status_code == 200
    assert client.delete(f"/api/v1/categories/{category_id}", headers=headers).status_code == 200


def test_frontend_contract_category_patch_and_dashboard_shape(client):
    token = register(client)
    headers = auth(token)
    category = client.post("/api/v1/categories", headers=headers, json={"name": "Home", "color": "#2563EB"}).get_json()["data"]
    renamed = client.patch(
        f"/api/v1/categories/{category['id']}", headers=headers, json={"name": "Personal", "color": "#16A34A"}
    )
    assert renamed.status_code == 200
    assert renamed.get_json()["data"]["name"] == "Personal"

    task = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"title": "Frontend contract", "category_id": category["id"], "priority": "medium"},
    ).get_json()["data"]
    updated = client.patch(f"/api/v1/tasks/{task['id']}", headers=headers, json={"priority": "high"})
    assert updated.status_code == 200
    assert updated.get_json()["data"]["priority"] == "high"

    dashboard = client.get("/api/v1/dashboard", headers=headers).get_json()["data"]
    assert dashboard["counts"]["total"] == 1
    assert dashboard["completion_percentage"] == 0.0
    assert isinstance(dashboard["upcoming_deadlines"], list)


def test_deleting_category_leaves_task_uncategorized(client):
    token = register(client)
    headers = auth(token)
    category = client.post("/api/v1/categories", headers=headers, json={"name": "Temporary", "color": "#64748B"}).get_json()["data"]
    task = client.post("/api/v1/tasks", headers=headers, json={"title": "Keep me", "category_id": category["id"]}).get_json()["data"]

    assert client.delete(f"/api/v1/categories/{category['id']}", headers=headers).status_code == 200
    persisted = client.get(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert persisted.status_code == 200
    assert persisted.get_json()["data"]["category"] is None


def test_data_is_isolated_per_user(client):
    first = register(client, "first@example.com")
    second = register(client, "second@example.com")
    task = client.post("/api/v1/tasks", headers=auth(first), json={"title": "Private"}).get_json()["data"]
    assert client.get(f"/api/v1/tasks/{task['id']}", headers=auth(second)).status_code == 404
    assert client.get("/api/v1/tasks", headers=auth(second)).get_json()["data"]["pagination"]["total"] == 0


def test_dashboard_statistics_and_overdue_logic(client):
    token = register(client)
    headers = auth(token)
    client.post("/api/v1/tasks", headers=headers, json={"title": "Late", "due_date": "2020-01-01", "status": "pending"})
    client.post("/api/v1/tasks", headers=headers, json={"title": "Done", "due_date": "2020-01-01", "status": "completed"})
    dashboard = client.get("/api/v1/dashboard", headers=headers)
    assert dashboard.status_code == 200
    data = dashboard.get_json()["data"]
    assert data["counts"] == {"total": 2, "pending": 1, "in_progress": 0, "completed": 1, "overdue": 1}
    assert data["completion_percentage"] == 50.0


def test_consistent_errors_and_invalid_filters(client):
    assert client.get("/api/v1/tasks").get_json() == {
        "success": False,
        "error": {"code": "authentication_required", "message": "A Bearer token is required", "details": None},
    }
    token = register(client)
    response = client.get("/api/v1/tasks?sort_by=malicious", headers=auth(token))
    assert response.status_code == 400
    assert response.get_json()["success"] is False

