
from fastapi.testclient import TestClient

from app.core.security import create_access_token

REGISTER_URL = "/api/v1/auth/register"
ME_URL = "/api/v1/auth/me"


def register_test_user(client: TestClient) -> dict:
    response = client.post(
        REGISTER_URL,
        json={
            "email": "me-test@example.com",
            "password": "a-long-test-password-123",
            "display_name": "Me Test",
        },
    )

    assert response.status_code == 201
    return response.json()


def test_me_returns_current_user(client: TestClient) -> None:
    registered_user = register_test_user(client)
    token = create_access_token(registered_user["id"])

    response = client.get(
        ME_URL,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == registered_user["id"]
    assert data["email"] == registered_user["email"]
    assert data["display_name"] == registered_user["display_name"]
    assert "password_hash" not in data


def test_me_rejects_missing_token(client: TestClient) -> None:
    response = client.get(ME_URL)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get(
        ME_URL,
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401


def test_me_rejects_expired_token(
    client: TestClient,
    db_session,
) -> None:
    from datetime import UTC, datetime, timedelta

    import jwt

    from app.core.config import settings
    from app.core.security import JWT_ALGORITHM

    expired_token = jwt.encode(
        {
            "sub": "1",
            "iat": datetime.now(UTC) - timedelta(minutes=20),
            "exp": datetime.now(UTC) - timedelta(minutes=10),
        },
        settings.jwt_secret_key.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )

    response = client.get(
        ME_URL,
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_me_rejects_token_for_nonexistent_user(
    client: TestClient,
) -> None:
    token = create_access_token(999999999)

    response = client.get(
        ME_URL,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401