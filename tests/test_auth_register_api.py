from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


def test_register_returns_created_user(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "developer@example.com",
            "password": "a-long-secure-password",
            "display_name": "Indie Developer",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] is not None
    assert data["email"] == "developer@example.com"
    assert data["display_name"] == "Indie Developer"
    assert data["created_at"] is not None


def test_register_normalizes_email_and_display_name(
    client: TestClient,
):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "  TEST@example.com  ",
            "password": "a-long-secure-password",
            "display_name": "  Test Developer  ",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "test@example.com"
    assert data["display_name"] == "Test Developer"


def test_register_rejects_duplicate_email(client: TestClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "a-long-secure-password",
        "display_name": "First User",
    }

    first_response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    duplicate_response = client.post(
        "/api/v1/auth/register",
        json=payload,
    )

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert (
        duplicate_response.json()["error"]["code"]
        == "EMAIL_ALREADY_REGISTERED"
    )


def test_register_rejects_invalid_email(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "a-long-secure-password",
            "display_name": "Test Developer",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_rejects_short_password(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "short-password@example.com",
            "password": "too-short",
            "display_name": "Test Developer",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_never_exposes_password_hash(
    client: TestClient,
    db_session: Session,
):
    password = "a-long-secure-password"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "security@example.com",
            "password": password,
            "display_name": "Security Test",
        },
    )

    assert response.status_code == 201

    response_data = response.json()

    assert "password" not in response_data
    assert "password_hash" not in response_data

    user = db_session.scalar(
        select(User).where(User.email == "security@example.com")
    )

    assert user is not None
    assert user.password_hash != password
    assert verify_password(password, user.password_hash)
def test_register_rejects_missing_fields(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={},
    )

    assert response.status_code == 422

    data = response.json()

    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert data["error"]["details"]

def test_register_rejects_blank_display_name(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "blank-name@example.com",
            "password": "a-long-secure-password",
            "display_name": "     ",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"