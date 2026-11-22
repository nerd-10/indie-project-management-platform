from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import auth as auth_api
from app.core.config import settings
from app.core.rate_limiter import SlidingWindowRateLimiter
from app.core.security import decode_access_token
from app.main import app

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

@pytest.fixture
def reset_login_limiters(monkeypatch):
    account_limiter = SlidingWindowRateLimiter(
        max_attempts=5,
        window_seconds=900,
    )
    ip_limiter = SlidingWindowRateLimiter(
        max_attempts=20,
        window_seconds=900,
    )

    monkeypatch.setattr(
        auth_api,
        "account_login_limiter",
        account_limiter,
    )
    monkeypatch.setattr(
        auth_api,
        "ip_login_limiter",
        ip_limiter,
    )

    return account_limiter, ip_limiter

def test_login_rate_limits_failed_attempts_per_account(
    client: TestClient,
    reset_login_limiters,
) -> None:
    register_test_user(client)

    payload = {
        "email": "login-test@example.com",
        "password": "incorrect-password",
    }

    for _ in range(5):
        response = client.post(LOGIN_URL, json=payload)
        assert response.status_code == 401

    response = client.post(LOGIN_URL, json=payload)

    assert response.status_code == 429
    assert "retry-after" in response.headers

def test_login_rate_limits_attempts_per_ip(
    client: TestClient,
    reset_login_limiters,
) -> None:
    for attempt in range(20):
        response = client.post(
            LOGIN_URL,
            json={
                "email": f"user{attempt}@example.com",
                "password": "incorrect-password",
            },
        )

        assert response.status_code == 401

    response = client.post(
        LOGIN_URL,
        json={
            "email": "another-user@example.com",
            "password": "incorrect-password",
        },
    )

    assert response.status_code == 429
    assert "retry-after" in response.headers

def test_successful_login_releases_rate_limit_reservations(
    client: TestClient,
    reset_login_limiters,
) -> None:
    register_test_user(client)

    payload = {
        "email": "login-test@example.com",
        "password": "a-long-test-password-123",
    }

    for _ in range(5):
        response = client.post(LOGIN_URL, json=payload)
        assert response.status_code == 200

    response = client.post(LOGIN_URL, json=payload)

    assert response.status_code == 200

def test_ip_limit_rejection_releases_account_reservation(
    client: TestClient,
    reset_login_limiters,
) -> None:
    account_limiter, ip_limiter = reset_login_limiters

    for _ in range(20):
        reservation = ip_limiter.try_acquire("testclient")
        assert reservation is not None

    response = client.post(
        LOGIN_URL,
        json={
            "email": "rollback-test@example.com",
            "password": "incorrect-password",
        },
    )

    assert response.status_code == 429

    # The account reservation should have been released.
    assert account_limiter.get_retry_after(
        ("rollback-test@example.com", "testclient")
    ) == 0

def test_login_releases_reservations_on_authentication_error(
    client: TestClient,
    reset_login_limiters,
) -> None:
    account_limiter, ip_limiter = reset_login_limiters

    with patch(
        "app.api.v1.auth.authenticate_user",
        side_effect=RuntimeError("Database unavailable"),
    ), TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.post(
            LOGIN_URL,
        json={
            "email": "error-test@example.com",
            "password": "incorrect-password",
        },
        )

    assert response.status_code == 500

    assert account_limiter.get_retry_after(
        ("error-test@example.com", "testclient")
    ) == 0

    assert ip_limiter.get_retry_after("testclient") == 0