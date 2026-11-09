from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.user import UserRegister, UserResponse


def test_registration_normalize_email_and_display_name():
    user = UserRegister(
        email = " DEVELOPER@EXAMPLE.COM ",
        password = "A-strong-password-123",
        display_name = " Game Developer ",
    )
    assert user.email == "developer@example.com"
    assert user.display_name == "Game Developer"

def test_registration_preserves_password_exactly():
    password = " A-strong-password-123 "

    user = UserRegister(
        email = "developer@example.com",
        password = password,
        display_name = "Game Developer",
    )
    assert user.password == password

def test_registration_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserRegister(
            email = "not-an-email",
            password = "A-strong-password-123",
            display_name = "Game Developer",
        )

@pytest.mark.parametrize(
    "password",
    [
        "Short123!",
        "A"*129,
    ],
)
def test_registration_rejects_password_outside_length_limits(password):
    with pytest.raises(ValidationError):
        UserRegister(
            email = "developer@example.com",
            password = password,
            display_name = "Game Developer",
        )

@pytest.mark.parametrize(
    "display_name",
    [
        "",
        "   ",
        "A"*101,
    ],
)
def test_registration_rejects_invalid_display_name(display_name):
    with pytest.raises(ValidationError):
        UserRegister(
            email = "developer@example.com",
            password = "A-strong-password-123",
            display_name = display_name,
        )

def test_user_response_does_not_expose_password_hash():
    database_user = SimpleNamespace(
        id = 1,
        email = "developer@example.com",
        display_name = "Game Developer",
        created_at = datetime.now(UTC),
        password_hash = "$argonid2$some-secret-hash",
    )

    response = UserResponse.model_validate(database_user)

    assert response.id == 1
    assert response.email == "developer@example.com"
    assert "password_hash" not in response.model_dump()
    assert "$argonid2some-secret-hash$" not in response.model_dump_json()