from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import decode_access_token

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"


def register_test_user(client: TestClient) -> dict:
    response = client.post(
        REGISTER_URL,
        json={
            "email": "login-test@example.com",
            "password": "a-long-test-password-123",
            "display_name": "Login Test",
        },
    )

    assert response.status_code == 201
    return response.json()


def test_login_returns_valid_access_token(client: TestClient) -> None:
    user = register_test_user(client)

    response = client.post(
        LOGIN_URL,
        json={
            "email": "login-test@example.com",
            "password": "a-long-test-password-123",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data

    claims = decode_access_token(data["access_token"])

    assert claims["sub"] == str(user["id"])
    assert claims["exp"] - claims["iat"] == (
        settings.jwt_access_token_expire_minutes * 60
    )


def test_login_rejects_incorrect_password(client: TestClient) -> None:
    register_test_user(client)

    response = client.post(
        LOGIN_URL,
        json={
            "email": "login-test@example.com",
            "password": "an-incorrect-password",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["message"] == (
        "Invalid email or password"
    )


def test_login_rejects_unknown_email(client: TestClient) -> None:
    response = client.post(
        LOGIN_URL,
        json={
            "email": "unknown@example.com",
            "password": "a-long-test-password-123",
        },
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["error"]["message"] == (
        "Invalid email or password"
    )


def test_login_uses_same_error_for_unknown_email_and_wrong_password(
    client: TestClient,
) -> None:
    register_test_user(client)

    wrong_password_response = client.post(
        LOGIN_URL,
        json={
            "email": "login-test@example.com",
            "password": "incorrect-password",
        },
    )

    unknown_email_response = client.post(
        LOGIN_URL,
        json={
            "email": "unknown@example.com",
            "password": "a-long-test-password-123",
        },
    )

    wrong_error = wrong_password_response.json()["error"]
    unknown_error = unknown_email_response.json()["error"]

    assert wrong_password_response.status_code == 401
    assert unknown_email_response.status_code == 401
    assert wrong_error["code"] == unknown_error["code"]
    assert wrong_error["message"] == unknown_error["message"]


def test_login_rejects_invalid_email(client: TestClient) -> None:
    response = client.post(
        LOGIN_URL,
        json={
            "email": "not-an-email",
            "password": "a-long-test-password-123",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_rejects_missing_fields(client: TestClient) -> None:
    response = client.post(
        LOGIN_URL,
        json={"email": "login-test@example.com"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"