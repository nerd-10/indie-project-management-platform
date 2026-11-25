from fastapi.testclient import TestClient

from app.core.security import create_access_token

PROJECTS_URL = "/api/v1/projects"


def create_authenticated_user(
    client: TestClient,
    email: str,
    display_name: str = "Test Developer",
) -> tuple[dict, dict]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "a-long-test-password-123",
            "display_name": display_name,
        },
    )

    assert response.status_code == 201

    user = response.json()
    token = create_access_token(user["id"])

    headers = {"Authorization": f"Bearer {token}"}

    return user, headers


def test_create_project_returns_created_project(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "project-owner@example.com",
    )

    response = client.post(
        PROJECTS_URL,
        headers=headers,
        json={
            "name": "My Indie Game",
            "description": "A small adventure game.",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["name"] == "My Indie Game"
    assert data["description"] == "A small adventure game."
    assert data["created_at"] is not None
    assert data["updated_at"] is not None
    assert "owner_id" not in data


def test_create_project_rejects_missing_token(client: TestClient):
    response = client.post(
        PROJECTS_URL,
        json={"name": "Unauthorized Project"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_create_project_rejects_invalid_token(client: TestClient):
    response = client.post(
        PROJECTS_URL,
        headers={"Authorization": "Bearer invalid-token"},
        json={"name": "Unauthorized Project"},
    )

    assert response.status_code == 401


def test_create_project_rejects_owner_id(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "protected-field@example.com",
    )

    response = client.post(
        PROJECTS_URL,
        headers=headers,
        json={
            "name": "My Project",
            "owner_id": 999999,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_projects_returns_only_current_users_projects(
    client: TestClient,
):
    _, owner_headers = create_authenticated_user(
        client,
        "list-owner@example.com",
    )

    _, another_headers = create_authenticated_user(
        client,
        "list-another@example.com",
    )

    client.post(
        PROJECTS_URL,
        headers=owner_headers,
        json={"name": "Owner Project"},
    )

    client.post(
        PROJECTS_URL,
        headers=another_headers,
        json={"name": "Another User Project"},
    )

    response = client.get(
        PROJECTS_URL,
        headers=owner_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "Owner Project"
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert data["has_more"] is False


def test_list_projects_rejects_missing_token(client: TestClient):
    response = client.get(PROJECTS_URL)

    assert response.status_code == 401


def test_list_projects_rejects_invalid_limit(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "invalid-limit@example.com",
    )

    response = client.get(
        PROJECTS_URL,
        headers=headers,
        params={"limit": 101},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_projects_rejects_negative_offset(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "negative-offset@example.com",
    )

    response = client.get(
        PROJECTS_URL,
        headers=headers,
        params={"offset": -1},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_retrieve_project_returns_owned_project(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "retrieve-owner@example.com",
    )

    create_response = client.post(
        PROJECTS_URL,
        headers=headers,
        json={
            "name": "My Project",
            "description": "Project description",
        },
    )

    project_id = create_response.json()["id"]

    response = client.get(
        f"{PROJECTS_URL}/{project_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == project_id
    assert response.json()["name"] == "My Project"
    assert "owner_id" not in response.json()


def test_retrieve_project_returns_404_for_another_user(
    client: TestClient,
):
    _, owner_headers = create_authenticated_user(
        client,
        "retrieve-project-owner@example.com",
    )

    _, another_headers = create_authenticated_user(
        client,
        "retrieve-project-another@example.com",
    )

    create_response = client.post(
        PROJECTS_URL,
        headers=owner_headers,
        json={"name": "Private Project"},
    )

    project_id = create_response.json()["id"]

    response = client.get(
        f"{PROJECTS_URL}/{project_id}",
        headers=another_headers,
    )

    assert response.status_code == 404


def test_retrieve_nonexistent_project_returns_404(
    client: TestClient,
):
    _, headers = create_authenticated_user(
        client,
        "retrieve-missing@example.com",
    )

    response = client.get(
        f"{PROJECTS_URL}/999999999",
        headers=headers,
    )

    assert response.status_code == 404


def test_retrieve_project_rejects_missing_token(
    client: TestClient,
):
    response = client.get(f"{PROJECTS_URL}/1")

    assert response.status_code == 401


def test_update_project_changes_name(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "patch-name@example.com",
    )

    created = client.post(
        PROJECTS_URL,
        headers=headers,
        json={
            "name": "Original Name",
            "description": "Original description",
        },
    )

    project_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}",
        headers=headers,
        json={"name": "Updated Name"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"
    assert response.json()["description"] == "Original description"


def test_update_project_can_clear_description(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "patch-description@example.com",
    )

    created = client.post(
        PROJECTS_URL,
        headers=headers,
        json={
            "name": "My Project",
            "description": "Description to clear",
        },
    )

    project_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}",
        headers=headers,
        json={"description": None},
    )

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_update_project_rejects_null_name(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "patch-null-name@example.com",
    )

    created = client.post(
        PROJECTS_URL,
        headers=headers,
        json={"name": "My Project"},
    )

    project_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}",
        headers=headers,
        json={"name": None},
    )

    assert response.status_code == 422


def test_update_project_rejects_empty_payload(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "patch-empty@example.com",
    )

    created = client.post(
        PROJECTS_URL,
        headers=headers,
        json={"name": "My Project"},
    )

    project_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}",
        headers=headers,
        json={},
    )

    assert response.status_code == 422


def test_update_project_rejects_protected_fields(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "patch-protected@example.com",
    )

    created = client.post(
        PROJECTS_URL,
        headers=headers,
        json={"name": "My Project"},
    )

    project_id = created.json()["id"]

    for field, value in [
        ("id", 999),
        ("owner_id", 999),
        ("created_at", "2026-01-01T00:00:00Z"),
        ("updated_at", "2026-01-01T00:00:00Z"),
    ]:
        response = client.patch(
            f"{PROJECTS_URL}/{project_id}",
            headers=headers,
            json={field: value},
        )

        assert response.status_code == 422


def test_update_project_rejects_another_users_project(
    client: TestClient,
):
    _, owner_headers = create_authenticated_user(
        client,
        "patch-owner@example.com",
    )

    _, another_headers = create_authenticated_user(
        client,
        "patch-another@example.com",
    )

    created = client.post(
        PROJECTS_URL,
        headers=owner_headers,
        json={"name": "Private Project"},
    )

    project_id = created.json()["id"]

    response = client.patch(
        f"{PROJECTS_URL}/{project_id}",
        headers=another_headers,
        json={"name": "Unauthorized Change"},
    )

    assert response.status_code == 404


def test_update_project_rejects_missing_token(client: TestClient):
    response = client.patch(
        f"{PROJECTS_URL}/1",
        json={"name": "Unauthorized Change"},
    )

    assert response.status_code == 401


def test_delete_project_returns_no_content(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "delete-owner@example.com",
    )

    created = client.post(
        PROJECTS_URL,
        headers=headers,
        json={"name": "Project to delete"},
    )

    project_id = created.json()["id"]

    response = client.delete(
        f"{PROJECTS_URL}/{project_id}",
        headers=headers,
    )

    assert response.status_code == 204
    assert response.content == b""

    retrieve_response = client.get(
        f"{PROJECTS_URL}/{project_id}",
        headers=headers,
    )

    assert retrieve_response.status_code == 404


def test_delete_project_rejects_another_users_project(
    client: TestClient,
):
    _, owner_headers = create_authenticated_user(
        client,
        "delete-project-owner@example.com",
    )

    _, another_headers = create_authenticated_user(
        client,
        "delete-project-another@example.com",
    )

    created = client.post(
        PROJECTS_URL,
        headers=owner_headers,
        json={"name": "Private Project"},
    )

    project_id = created.json()["id"]

    response = client.delete(
        f"{PROJECTS_URL}/{project_id}",
        headers=another_headers,
    )

    assert response.status_code == 404


def test_delete_nonexistent_project_returns_404(
    client: TestClient,
):
    _, headers = create_authenticated_user(
        client,
        "delete-missing@example.com",
    )

    response = client.delete(
        f"{PROJECTS_URL}/999999999",
        headers=headers,
    )

    assert response.status_code == 404


def test_delete_project_rejects_missing_token(
    client: TestClient,
):
    response = client.delete(f"{PROJECTS_URL}/1")

    assert response.status_code == 401

def test_create_project_rejects_missing_name(client: TestClient):
    _, headers = create_authenticated_user(
        client,
        "missing-project-name@example.com",
    )

    response = client.post(
        PROJECTS_URL,
        headers=headers,
        json={"description": "A project description."},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"