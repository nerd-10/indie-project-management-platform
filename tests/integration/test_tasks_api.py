from fastapi.testclient import TestClient

from app.core.security import create_access_token

PROJECTS_URL = "/api/v1/projects"


def create_authenticated_user(
    client: TestClient,
    email: str,
) -> tuple[dict, dict]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "a-long-test-password-123",
            "display_name": "Test Developer",
        },
    )

    assert response.status_code == 201

    user = response.json()
    token = create_access_token(user["id"])
    headers = {"Authorization": f"Bearer {token}"}

    return user, headers


def create_project(
    client: TestClient,
    headers: dict,
    name: str = "Test Project",
) -> int:
    response = client.post(
        PROJECTS_URL,
        headers=headers,
        json={"name": name},
    )

    assert response.status_code == 201
    return response.json()["id"]


def test_create_task_returns_created_task(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "create-task-owner@example.com",
    )
    project_id = create_project(client, headers)

    response = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Implement player movement",
            "description": "Add keyboard-based movement.",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["project_id"] == project_id
    assert data["title"] == "Implement player movement"
    assert data["description"] == "Add keyboard-based movement."
    assert data["status"] == "todo"
    assert data["created_at"] is not None
    assert data["updated_at"] is not None
    assert "owner_id" not in data


def test_create_task_uses_default_values(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "create-defaults@example.com",
    )
    project_id = create_project(client, headers)

    response = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={"title": "Create main menu"},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "todo"
    assert response.json()["description"] is None


def test_create_task_rejects_missing_token(client: TestClient):
    response = client.post(
        f"{PROJECTS_URL}/1/tasks",
        json={"title": "Unauthorized task"},
    )

    assert response.status_code == 401


def test_create_task_rejects_invalid_token(client: TestClient):
    response = client.post(
        f"{PROJECTS_URL}/1/tasks",
        headers={"Authorization": "Bearer invalid-token"},
        json={"title": "Unauthorized task"},
    )

    assert response.status_code == 401


def test_create_task_rejects_another_users_project(client: TestClient):
    _, owner_headers = create_authenticated_user(
        client,
        "task-project-owner@example.com",
    )
    _, another_headers = create_authenticated_user(
        client,
        "task-project-another@example.com",
    )

    project_id = create_project(client, owner_headers)

    response = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=another_headers,
        json={"title": "Unauthorized task"},
    )

    assert response.status_code == 404


def test_create_task_rejects_nonexistent_project(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "task-missing-project@example.com",
    )

    response = client.post(
        f"{PROJECTS_URL}/999999999/tasks",
        headers=headers,
        json={"title": "Task"},
    )

    assert response.status_code == 404


def test_create_task_rejects_protected_fields(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "task-protected-fields@example.com",
    )
    project_id = create_project(client, headers)

    response = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Task",
            "project_id": 999,
            "id": 999,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_task_rejects_invalid_title(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "task-invalid-title@example.com",
    )
    project_id = create_project(client, headers)

    for title in ["", "   ", "a" * 201]:
        response = client.post(
            f"{PROJECTS_URL}/{project_id}/tasks",
            headers=headers,
            json={"title": title},
        )

        assert response.status_code == 422


def test_create_task_rejects_invalid_status(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "task-invalid-status@example.com",
    )
    project_id = create_project(client, headers)

    response = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Task",
            "status": "blocked",
        },
    )

    assert response.status_code == 422


def test_create_task_rejects_long_description(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "task-long-description@example.com",
    )
    project_id = create_project(client, headers)

    response = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Task",
            "description": "a" * 10001,
        },
    )

    assert response.status_code == 422

def test_retrieve_task_returns_task_from_project(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "retrieve-task-owner@example.com",
    )
    project_id = create_project(client, headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={"title": "Find this task"},
    )
    task_id = created.json()["id"]

    response = client.get(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == task_id
    assert response.json()["project_id"] == project_id
    assert response.json()["title"] == "Find this task"


def test_retrieve_task_rejects_another_users_project(
    client: TestClient,
):
    _, owner_headers = create_authenticated_user(
        client,
        "retrieve-task-project-owner@example.com",
    )
    _, another_headers = create_authenticated_user(
        client,
        "retrieve-task-project-another@example.com",
    )

    project_id = create_project(client, owner_headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=owner_headers,
        json={"title": "Private task"},
    )
    task_id = created.json()["id"]

    response = client.get(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=another_headers,
    )

    assert response.status_code == 404


def test_retrieve_task_rejects_incorrect_project_id(
    client: TestClient,
):
    _, headers = create_authenticated_user(
        client,
        "retrieve-task-mismatch@example.com",
    )

    project_one = create_project(client, headers, "Project One")
    project_two = create_project(client, headers, "Project Two")

    created = client.post(
        f"{PROJECTS_URL}/{project_one}/tasks",
        headers=headers,
        json={"title": "Task in project one"},
    )
    task_id = created.json()["id"]

    response = client.get(
        f"{PROJECTS_URL}/{project_two}/tasks/{task_id}",
        headers=headers,
    )

    assert response.status_code == 404


def test_retrieve_nonexistent_task_returns_404(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "retrieve-task-missing@example.com",
    )
    project_id = create_project(client, headers)

    response = client.get(
        f"{PROJECTS_URL}/{project_id}/tasks/999999999",
        headers=headers,
    )

    assert response.status_code == 404


def test_retrieve_task_rejects_missing_token(client: TestClient):
    response = client.get(f"{PROJECTS_URL}/1/tasks/1")

    assert response.status_code == 401

def test_update_task_changes_title(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "update-task-title@example.com",
    )
    project_id = create_project(client, headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Original title",
            "description": "Original description",
        },
    )
    task_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=headers,
        json={"title": "Updated title"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"
    assert response.json()["description"] == "Original description"


def test_update_task_can_clear_description(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "update-task-description@example.com",
    )
    project_id = create_project(client, headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Task",
            "description": "Description to clear",
        },
    )
    task_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=headers,
        json={"description": None},
    )

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_update_task_can_change_status(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "update-task-status@example.com",
    )
    project_id = create_project(client, headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={"title": "Task"},
    )
    task_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=headers,
        json={"status": "in_progress"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_update_task_rejects_empty_payload(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "update-task-empty@example.com",
    )
    project_id = create_project(client, headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={"title": "Task"},
    )
    task_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=headers,
        json={},
    )

    assert response.status_code == 422


def test_update_task_rejects_null_title(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "update-task-null-title@example.com",
    )
    project_id = create_project(client, headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={"title": "Task"},
    )
    task_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=headers,
        json={"title": None},
    )

    assert response.status_code == 422


def test_update_task_rejects_null_status(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "update-task-null-status@example.com",
    )
    project_id = create_project(client, headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={"title": "Task"},
    )
    task_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=headers,
        json={"status": None},
    )

    assert response.status_code == 422


def test_update_task_rejects_protected_fields(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "update-task-protected@example.com",
    )
    project_id = create_project(client, headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={"title": "Task"},
    )
    task_id = created.json()["id"]

    for field, value in [
        ("id", 999),
        ("project_id", 999),
        ("created_at", "2026-01-01T00:00:00Z"),
        ("updated_at", "2026-01-01T00:00:00Z"),
    ]:
        response = client.patch(
            f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
            headers=headers,
            json={field: value},
        )

        assert response.status_code == 422


def test_update_task_rejects_another_users_project(
    client: TestClient,
):
    _, owner_headers = create_authenticated_user(
        client,
        "update-task-owner@example.com",
    )
    _, another_headers = create_authenticated_user(
        client,
        "update-task-another@example.com",
    )

    project_id = create_project(client, owner_headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=owner_headers,
        json={"title": "Private task"},
    )
    task_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=another_headers,
        json={"title": "Unauthorized change"},
    )

    assert response.status_code == 404


def test_update_task_rejects_incorrect_project_id(
    client: TestClient,
):
    _, headers = create_authenticated_user(
        client,
        "update-task-mismatch@example.com",
    )

    project_one = create_project(client, headers, "Project One")
    project_two = create_project(client, headers, "Project Two")

    created = client.post(
        f"{PROJECTS_URL}/{project_one}/tasks",
        headers=headers,
        json={"title": "Task in project one"},
    )
    task_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_two}/tasks/{task_id}",
        headers=headers,
        json={"title": "Unauthorized change"},
    )

    assert response.status_code == 404


def test_update_task_rejects_missing_token(client: TestClient):
    response = client.patch(
        f"{PROJECTS_URL}/1/tasks/1",
        json={"title": "Unauthorized change"},
    )

    assert response.status_code == 401

def test_delete_task_returns_no_content(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "delete-task-owner@example.com",
    )
    project_id = create_project(client, headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=headers,
        json={"title": "Task to delete"},
    )
    task_id = created.json()["id"]

    response = client.delete(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=headers,
    )

    assert response.status_code == 204
    assert response.content == b""

    retrieve_response = client.get(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=headers,
    )

    assert retrieve_response.status_code == 404


def test_delete_task_rejects_another_users_project(
    client: TestClient,
):
    _, owner_headers = create_authenticated_user(
        client,
        "delete-task-owner-private@example.com",
    )
    _, another_headers = create_authenticated_user(
        client,
        "delete-task-another-private@example.com",
    )

    project_id = create_project(client, owner_headers)

    created = client.post(
        f"{PROJECTS_URL}/{project_id}/tasks",
        headers=owner_headers,
        json={"title": "Private task"},
    )
    task_id = created.json()["id"]

    response = client.delete(
        f"{PROJECTS_URL}/{project_id}/tasks/{task_id}",
        headers=another_headers,
    )

    assert response.status_code == 404


def test_delete_task_rejects_incorrect_project_id(
    client: TestClient,
):
    _, headers = create_authenticated_user(
        client,
        "delete-task-mismatch@example.com",
    )

    project_one = create_project(client, headers, "Project One")
    project_two = create_project(client, headers, "Project Two")

    created = client.post(
        f"{PROJECTS_URL}/{project_one}/tasks",
        headers=headers,
        json={"title": "Task in project one"},
    )
    task_id = created.json()["id"]

    response = client.delete(
        f"{PROJECTS_URL}/{project_two}/tasks/{task_id}",
        headers=headers,
    )

    assert response.status_code == 404


def test_delete_nonexistent_task_returns_404(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "delete-task-missing@example.com",
    )
    project_id = create_project(client, headers)

    response = client.delete(
        f"{PROJECTS_URL}/{project_id}/tasks/999999999",
        headers=headers,
    )

    assert response.status_code == 404


def test_delete_task_rejects_missing_token(client: TestClient):
    response = client.delete(f"{PROJECTS_URL}/1/tasks/1")

    assert response.status_code == 401
