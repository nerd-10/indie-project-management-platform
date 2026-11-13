import pytest
from pydantic import ValidationError

from app.schemas.user import TokenResponse, UserLogin


def test_login_normalize_email():
    login = UserLogin(
        email = " DEVELOPER@EXAMPLE.COM ",
        password = " A-STRONG-PASSWORD-123 ",
    )

    assert login.email == "developer@example.com"

def test_login_preserves_password_exactly():
    password = " A-STRONG-PASSWORD-123 "
    login = UserLogin(
        email = "developer@example.com",
        password = password,
    )
    assert login.password == password

def test_rejects_invalid_email():
    with pytest.raises(ValidationError):
        UserLogin(
            email = "not-an-email",
            password = "A-STRONG-PASSWORD-123",
        )
@pytest.mark.parametrize(
    "password",
    [
        "",
        "A" * 129,
    ],
)
def test_login_rejects_invalid_password_length(password):
    with pytest.raises(ValidationError):
        UserLogin(
            email = "not-an-email",
            password = password,
        )

def test_token_response_defaults_to_bearer():
    response = TokenResponse(
        access_token = "example-token",
    )
    assert response.token_type == "bearer"